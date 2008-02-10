#!/usr/bin/env python
import pygtk
pygtk.require('2.0')

import os
import gtk
import gtk.glade

from hamster import dispatcher, storage, SHARED_DATA_DIR

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

class CategoryStore(gtk.ListStore):
    columns = ['id', 'name', 'color_code', 'category_order']

    def __init__(self):
        #id, name, color_code, order
        gtk.ListStore.__init__(self, int, str, str, int)

    def load(self):
        """ Loads activity list from database, ordered by
            activity_order """

        category_list = storage.get_category_list()

        for category in category_list:
            self.append(ordered_list(category, self.columns)) #performing the magic, so we don't risk with database field order change
        
        self.append([-1, "Unsorted", "", 999]) # all activities without category

    def value(self, path, column):
        return self[path][self.columns.index(column)]

    def update(self, path, column, new_value):
        self[path][self.columns.index(column)] = new_value


class ActivityStore(gtk.ListStore):
    columns = ['id', 'name', 'category_id', 'activity_order']

    def __init__(self):
        #id, name, category_id, order
        gtk.ListStore.__init__(self, int, str, int, int)

    def load(self, category_id):
        """ Loads activity list from database, ordered by
            activity_order """
            
        self.clear()

        if category_id == None:
            return
        
        activity_list = storage.get_activities(category_id)

        for activity in activity_list:
            self.append(ordered_list(activity, self.columns)) #performing the magic, so we don't risk with database field order change

    def value(self, path, column):
        return self[path][self.columns.index(column)]

    def update(self, path, column, new_value):
        self[path][self.columns.index(column)] = new_value

class ActivitiesEditor:
    TARGETS = [
        ('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_WIDGET, 0),
        ('text/plain', 0, 1),
        ('TEXT', 0, 2),
        ('STRING', 0, 3),
        ]

    def __init__(self):
        self.wTree = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, "activities.glade"))
        self.window = self.get_widget('activities_window')

        # create and fill store with activities
        self.store = ActivityStore()
        #self.store.load() #get data from DB
        
        self.category_store = CategoryStore()
        self.category_store.load()

        self.configure_tree()
        self.configure_categories()
        self.wTree.signal_autoconnect(self)

        # Allow enable drag and drop of rows including row move
        self.treeview.enable_model_drag_source( gtk.gdk.BUTTON1_MASK,
                                                self.TARGETS,
                                                gtk.gdk.ACTION_DEFAULT|
                                                gtk.gdk.ACTION_MOVE)
        self.treeview.enable_model_drag_dest(self.TARGETS,
                                             gtk.gdk.ACTION_DEFAULT)

        self.category_tree.enable_model_drag_dest(self.TARGETS,
                                             gtk.gdk.ACTION_DEFAULT)

        self.treeview.connect("drag_data_get", self.drag_data_get_data)
        self.treeview.connect("drag_data_received",
                              self.drag_data_received_data)

    def drag_data_get_data(self, treeview, context, selection, target_id,
                           etime):
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        data = model.get_value(iter, 0) #get activity ID
        selection.set(selection.target, 0, str(data))

    def select_activity(self, id):
        model = self.treeview.get_model()
        
        id_column = self.store.columns.index('id')
        
        i = 0
        for row in model:
            if row[id_column] == id:
                self.treeview.set_cursor((i, ))
            i += 1
                
        
    def drag_data_received_data(self, treeview, context, x, y, selection,
                                info, etime):
        model = treeview.get_model()
        data = selection.data
        drop_info = treeview.get_dest_row_at_pos(x, y)

        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            if (position == gtk.TREE_VIEW_DROP_BEFORE
                or position == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
                #model.insert_before(iter, [data])
                print "insert '%s' before '%s'" % (data, model[iter][3])
                storage.move_activity(int(data), model[iter][3], insert_after = False)
            else:
                #model.insert_after(iter, [data])
                print "insert '%s' after '%s'" % (data, model[iter][3])
                storage.move_activity(int(data), model[iter][3], insert_after = True)
        else:
            #model.append([data])
            print "append '%s'" % data

        if context.action == gtk.gdk.ACTION_MOVE:
            context.finish(True, True, etime)


        self.store.load(self._get_selected_category())

        self.select_activity(int(data))
        
        return





    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.wTree.get_widget(name)

    def get_store(self):
        """returns store, so we can add some watchers in case if anything changes"""
        return self.store

    def show(self):
        self.selection_changed_cb(self.treeview.get_selection(), self.store)
        self.window.show_all()

    def configure_categories(self):
        """ Fills store with activities, and connects it to tree """

        self.category_tree = treeview = self.get_widget('category_list')

        nameColumn = gtk.TreeViewColumn(_(u'Category'))
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()

        nameColumn.pack_start(nameCell, True)
        nameColumn.set_attributes(nameCell, text = self.store.columns.index('name'))
        nameColumn.set_sort_column_id(1)
        treeview.append_column(nameColumn)

        treeview.set_model(self.category_store)

        selection = treeview.get_selection()
        selection.connect('changed', self.category_changed_cb, self.category_store)


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

        treeview.set_model(self.store)


        self.selection = treeview.get_selection()
        self.selection.connect('changed', self.selection_changed_cb, self.store)

    def update_activity(self, tree_row):
        print "Update activity: ", tree_row[3]
        #map to dictionary, for easier updates
        row_data = {'name': tree_row[1],
                    'category_id': tree_row[2],
                      'id': tree_row[0]}

        # update id (necessary for new records)
        tree_row[0] = storage.update_activity(row_data)

    # callbacks
    def name_edited_cb(self, cell, path, new_text, model):
        model.update(path, 'name', new_text)
        self.update_activity(model[path])
        return True

    def category_changed_cb(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()

        if iter == None:
            self.store.clean()
        else:
            print model[iter][0]
            self.store.load(model[iter][0])

        return True

    def _get_selected_category(self):
        selection = self.get_widget('category_list').get_selection()
        (model, iter) = selection.get_selected()

        if iter:
            return model[iter][0]
        else:
            return None
        

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

        # override enabled buttons for unsorted category
        if self._get_selected_category() == -1:
            self.get_widget('promote_activity').set_sensitive(False)
            self.get_widget('demote_activity').set_sensitive(False)
            
        return True

    def delete_selected_activity(self):
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
        

    """keyboard events"""
    def on_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Delete):
        self.delete_selected_activity()
        
    """button events"""
    def on_add_activity_clicked(self, button):
        """ appends row, jumps to it and allows user to input name """
        category_id = self._get_selected_category()
        
        new_activity = self.store.append([-1, _(u"New activity"), category_id, -1])

        (model, iter) = self.selection.get_selected()

        self.treeview.set_cursor_on_cell(model.get_string_from_iter(new_activity),
                                         focus_column = self.treeview.get_column(0),
                                         focus_cell = None,
                                         start_editing = True)
        return

    def on_remove_activity_clicked(self, button):
        self.delete_selected_activity()

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


