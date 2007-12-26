#!/usr/bin/env python
import pygtk
pygtk.require('2.0')

import os
import gtk
import gtk.glade

from hamster import storage, SHARED_DATA_DIR

def get_prev(selection, model):
    (model, iter) = selection.get_selected()

    #previous item
    path = model.get_path(iter)[0] - 1
    if path >= 0:
        return model.get_iter_from_string(str(path))
    else:
        return None

def ordered_list(row, columns):
    #FIXME - i know there was some cool short way to map directly
    res = []
    for column in columns:
        res.append(row[column])
    return res

class ActivityStore(gtk.ListStore):
    columns = ['id', 'name', 'work', 'activity_order']

    def __init__(self):
        #id, name, work, order
        gtk.ListStore.__init__(self, int, str, 'gboolean', int)

    def load(self):
        """ Loads activity list from database, ordered by
            activity_order """

        activity_list = storage.get_activity_list()

        for activity in activity_list:
            self.append(ordered_list(activity, self.columns)) #performing the magick, so we don't risk with database field order change

    def value(self, path, column):
        return self[path][self.columns.index(column)]

    def update(self, path, column, new_value):
        self[path][self.columns.index(column)] = new_value

class ActivitiesEditor:
    def __init__(self):
        self.wTree = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, "activities.glade"))
        self.window = self.get_widget('activities_window')

        activities = storage.get_activity_list()

        # create and fill store with activities
        self.store = ActivityStore()
        self.store.load() #get data from DB

        self.configure_tree()
        self.wTree.signal_autoconnect(self)

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.wTree.get_widget(name)

    def get_store(self):
        """returns store, so we can add some watchers in case if anything changes"""
        return self.store

    def show(self):
        self.selection_changed_cb(self.treeview.get_selection(), self.store)
        self.window.show_all()

    def configure_tree(self):
        """ Fills store with activities, and connects it to tree """

        self.treeview = treeview = self.get_widget('activity_list')

        nameColumn = gtk.TreeViewColumn(_(u'Name'))
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()
        nameCell.set_property('editable', True)
        nameCell.connect('edited', self.name_edited_cb, self.store)
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_attributes(nameCell, text = self.store.columns.index('name'))
        nameColumn.set_sort_column_id(1)
        treeview.append_column(nameColumn)

        categoryColumn = gtk.TreeViewColumn(_(u'Work?'))
        categoryColumn.set_expand(False)
        categoryCell = gtk.CellRendererToggle()
        categoryCell.set_property('activatable', True);
        categoryCell.connect('toggled', self.work_toggled_cb, self.store)
        categoryColumn.pack_start(categoryCell, True)
        categoryColumn.set_attributes(categoryCell, active = self.store.columns.index('work'))
        treeview.append_column(categoryColumn)

        treeview.set_model(self.store)


        self.selection = treeview.get_selection()
        self.selection.connect('changed', self.selection_changed_cb, self.store)

    def update_activity(self, tree_row):
        print "Update activity: ", tree_row[3]
        #map to dictionary, for easier updates
        row_data = {'name': tree_row[1],
                    'work': tree_row[2],
                      'id': tree_row[0]}

        # update id (necessary for new records)
        tree_row[0] = storage.update_activity(row_data)

    # callbacks
    def work_toggled_cb(self, cell, path, model):
        model.update(path, 'work', not model.value(path, 'work')) #inverse
        self.update_activity(model[path])
        return True

    def name_edited_cb(self, cell, path, new_text, model):
        model.update(path, 'name', new_text)
        self.update_activity(model[path])
        return True

    def selection_changed_cb(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()

        if iter == None:
            self.get_widget('remove_activity').set_sensitive(False)
            self.get_widget('promote_activity').set_sensitive(False)
            self.get_widget('demote_activity').set_sensitive(False)
        else:
            self.get_widget('remove_activity').set_sensitive(True)

            first_item = model.get_path(iter) == (0,)
            self.get_widget('promote_activity').set_sensitive(not first_item)

            last_item = model.iter_next(iter) == None
            self.get_widget('demote_activity').set_sensitive(not last_item)
        return True

    #toolbar button clicks
    def on_add_activity_clicked(self, button):
        """ appends row, jumps to it and allows user to input name """
        new_activity = self.store.append([-1, _(u"New activity"), True, -1])

        (model, iter) = self.selection.get_selected()

        self.treeview.set_cursor_on_cell(model.get_string_from_iter(new_activity),
                                         focus_column = self.treeview.get_column(0),
                                         focus_cell = None,
                                         start_editing = True)
        return

    def on_remove_activity_clicked(self, button):
        (model, iter) = self.selection.get_selected()

        next_row = model.iter_next(iter)

        if next_row:
            self.selection.select_iter(next_row)
        else:
            path = self.store.get_path(iter)[0] - 1
            if path > 0:
                self.selection.select_path(path)

        storage.remove_activity(model[iter][0])
        model.remove(iter)
        return


    def on_promote_activity_clicked(self, button):
        (model, iter) = self.selection.get_selected()

        #previous item
        prev_iter = get_prev(self.selection, model)
        storage.swap_activities(model[iter][0], model[prev_iter][0])
        model.move_before(iter, prev_iter)

        self.selection_changed_cb(self.selection, model)
        dispatcher.dispatch('activity_updated', ())
        return

    def on_demote_activity_clicked(self, button):
        (model, iter) = self.selection.get_selected()

        next_iter = model.iter_next(iter)
        storage.swap_activities(model[iter][0], model[next_iter][0])
        self.store.move_after(iter, next_iter)

        self.selection_changed_cb(self.selection, model)
        dispatcher.dispatch('activity_updated', ())
        return


if __name__ == '__main__':
    controller = ActivitiesController()
    controller.show()
    gtk.main()


