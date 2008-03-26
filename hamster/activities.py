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

class CategoryStore(gtk.ListStore):
    def __init__(self):
        #id, name, color_code, order
        gtk.ListStore.__init__(self, int, str, int)

    def load(self):
        """ Loads activity list from database, ordered by
            activity_order """

        category_list = storage.get_category_list()

        for category in category_list:
            self.append([category['id'],
                         category['name'],
                         category['category_order']])
        
        self.append([-1, "Unsorted", 999]) # all activities without category


class ActivityStore(gtk.ListStore):
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
            self.append([activity['id'],
                         activity['name'],
                         activity['category_id'],
                         activity['activity_order']])

class ActivitiesEditor:
    TARGETS = [
        ('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_WIDGET, 0),
        ('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_APP, 0),
        ]
    
    
    def __init__(self):
        self.wTree = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, "activities.glade"))
        self.window = self.get_widget('activities_window')

        # create and fill activity tree
        self.activity_tree = self.get_widget('activity_list')
        self.activity_store = ActivityStore()

        nameColumn = gtk.TreeViewColumn(_(u'Name'))
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()
        nameCell.set_property('editable', True)
        nameCell.connect('edited', self.activity_name_edited_cb, self.activity_store)
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_attributes(nameCell, text = 1)
        nameColumn.set_sort_column_id(1)
        self.activity_tree.append_column(nameColumn)

        self.activity_tree.set_model(self.activity_store)

        self.selection = self.activity_tree.get_selection()
        self.selection.connect('changed', self.activity_changed, self.activity_store)


        # create and fill category tree
        self.category_tree = self.get_widget('category_list')
        self.category_store = CategoryStore()

        nameColumn = gtk.TreeViewColumn(_(u'Category'))
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()
        nameCell.set_property('editable', True)
        nameCell.connect('edited', self.category_edited_cb, self.category_store)

        nameColumn.pack_start(nameCell, True)
        nameColumn.set_attributes(nameCell, text = 1)
        nameColumn.set_sort_column_id(1)
        self.category_tree.append_column(nameColumn)

        self.category_store.load()
        self.category_tree.set_model(self.category_store)

        selection = self.category_tree.get_selection()
        selection.connect('changed', self.category_changed_cb, self.category_store)

        self.wTree.signal_autoconnect(self)

        # Allow enable drag and drop of rows including row move
        self.activity_tree.enable_model_drag_source( gtk.gdk.BUTTON1_MASK,
                                                self.TARGETS,
                                                gtk.gdk.ACTION_DEFAULT|
                                                gtk.gdk.ACTION_MOVE)
        self.activity_tree.enable_model_drag_dest(self.TARGETS,
                                                  gtk.gdk.ACTION_DEFAULT)

        self.category_tree.enable_model_drag_dest(self.TARGETS,
                                                  gtk.gdk.ACTION_DEFAULT)

        self.activity_tree.connect("drag_data_get", self.drag_data_get_data)
        self.activity_tree.connect("drag_data_received",
                                   self.drag_data_received_data)

        self.category_tree.connect("drag_data_received",
                                   self.on_category_drop)

        #select first category
        selection = self.category_tree.get_selection()
        selection.select_path((0,))


    def drag_data_get_data(self, treeview, context, selection, target_id,
                           etime):
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        data = model.get_value(iter, 0) #get activity ID
        selection.set(selection.target, 0, str(data))

    def select_activity(self, id):
        model = self.activity_tree.get_model()
        i = 0
        for row in model:
            if row[0] == id:
                self.activity_tree.set_cursor((i, ))
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


        self.activity_store.load(self._get_selected_category())

        self.select_activity(int(data))
        
        return


    def on_category_drop(self, treeview, context, x, y, selection,
                                info, etime):
        model = self.category_tree.get_model()
        data = selection.data
        drop_info = treeview.get_dest_row_at_pos(x, y)

        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            
            storage.change_category(int(data), model[iter][0])
            
            context.finish(True, True, etime)
        else:
            context.finish(False, True, etime)

        return




    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.wTree.get_widget(name)

    def get_store(self):
        """returns store, so we can add some watchers in case if anything changes"""
        return self.activity_store

    def show(self):
        self.window.show_all()

    def update_activity(self, tree_row):
        print "Update activity: ", tree_row[3]
        #map to dictionary, for easier updates
        name = tree_row[1]
        category_id = tree_row[2]
        id = tree_row[0]
        
        if id == -1:
            tree_row[0] = storage.insert_activity(name, category_id)
        else:
            storage.update_activity(id, name, category_id)

    # callbacks
    def category_edited_cb(self, cell, path, new_text, model):
        model[path][1] = new_text
        id = model[path][0]
        name = model[path][1]
        
        if id == -2:
            id = storage.insert_category(name)
            model[path][0] = id
        elif id > -1:  #ignore unsorted category (id = -1)
            storage.update_category(id, name)


    def activity_name_edited_cb(self, cell, path, new_text, model):
        model.update(path, 'name', new_text)
        self.update_activity(model[path])
        return True

    def category_changed_cb(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()
        id = 0
        if iter == None:
            self.activity_store.clear()
        else:
            id = model[iter][0]
            self.activity_store.load(model[iter][0])
        
        #do not allow to remove the unsorted category
        self.get_widget('remove_category').set_sensitive(id != -1)

        self.get_widget('promote_activity').set_sensitive(False)
        self.get_widget('demote_activity').set_sensitive(False)
        self.get_widget('remove_activity').set_sensitive(False)

        return True

    def _get_selected_category(self):
        selection = self.get_widget('category_list').get_selection()
        (model, iter) = selection.get_selected()

        if iter:
            return model[iter][0]
        else:
            return None
        

    def activity_changed(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()
        
        # treat any selected case
        self.get_widget('remove_activity').set_sensitive(iter != None)

        unsorted_selected = self._get_selected_category() == -1
        self.get_widget('promote_activity').set_sensitive(False)
        self.get_widget('demote_activity').set_sensitive(False)
        if iter != None and not unsorted_selected:
            first_item = model.get_path(iter) == (0,)
            self.get_widget('promote_activity').set_sensitive(not first_item)

            last_item = model.iter_next(iter) == None
            self.get_widget('demote_activity').set_sensitive(not last_item)

    def _del_selected_row(self, tree):
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()

        next_row = model.iter_next(iter)

        if next_row:
            selection.select_iter(next_row)
        else:
            path = model.get_path(iter)[0] - 1
            if path > 0:
                selection.select_path(path)

        removable_id = model[iter][0]
        model.remove(iter)
        return removable_id
        

    """keyboard events"""
    def on_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Delete):
        self.delete_selected_activity()
        
    """button events"""
    def on_add_category_clicked(self, button):
        """ appends row, jumps to it and allows user to input name """
        new_category = self.category_store.append([-2, _(u"New category"), -1])

        self.category_tree.set_cursor_on_cell((len(self.category_tree.get_model()) - 1, ),
                                         focus_column = self.category_tree.get_column(0),
                                         focus_cell = None,
                                         start_editing = True)

    def on_remove_category_clicked(self, button):
        removable_id = self._del_selected_row(self.category_tree)
        storage.remove_category(removable_id)
        
        

    def on_add_activity_clicked(self, button):
        """ appends row, jumps to it and allows user to input name """
        category_id = self._get_selected_category()
        
        new_activity = self.activity_store.append([-1, _(u"New activity"), category_id, -1])

        (model, iter) = self.selection.get_selected()

        self.activity_tree.set_cursor_on_cell(model.get_string_from_iter(new_activity),
                                         focus_column = self.activity_tree.get_column(0),
                                         focus_cell = None,
                                         start_editing = True)

    def on_remove_activity_clicked(self, button):
        removable_id = self._del_selected_row(self.activity_tree)
        storage.remove_activity(removable_id)

    def on_promote_activity_clicked(self, button):
        (model, iter) = self.selection.get_selected()

        #previous item
        prev_iter = get_prev(self.selection, model)
        storage.swap_activities(model[iter][0], model[prev_iter][0])
        model.move_before(iter, prev_iter)

        self.activity_changed(self.selection, model)

    def on_demote_activity_clicked(self, button):
        (model, iter) = self.selection.get_selected()

        next_iter = model.iter_next(iter)
        storage.swap_activities(model[iter][0], model[next_iter][0])
        self.activity_store.move_after(iter, next_iter)

        self.activity_changed(self.selection, model)


if __name__ == '__main__':
    controller = ActivitiesController()
    controller.show()
    gtk.main()
