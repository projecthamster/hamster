# -*- coding: utf-8 -*-

# Copyright (C) 2007, 2008 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.


import pygtk
pygtk.require('2.0')

import os
import gtk

from hamster import dispatcher, storage, SHARED_DATA_DIR, stuff
from hamster.Configuration import GconfStore

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
        
        self.unsorted_category = self.append([-1, _("Unsorted"), 999]) # all activities without category


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


formats = ["fixed", "symbolic", "minutes"]
appearances = ["text", "icon", "both"]

class PreferencesEditor:
    TARGETS = [
        ('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_WIDGET, 0),
        ('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_APP, 0),
        ]
    
    
    def __init__(self, parent = None):
        self.parent = parent
        self._gui = stuff.load_ui_file("preferences.ui")
        self.config = GconfStore.get_instance()
        self.window = self.get_widget('preferences_window')


        # create and fill activity tree
        self.activity_tree = self.get_widget('activity_list')
        self.get_widget("activities_label").set_mnemonic_widget(self.activity_tree)
        self.activity_store = ActivityStore()

        self.activityColumn = gtk.TreeViewColumn(_("Name"))
        self.activityColumn.set_expand(True)
        self.activityCell = gtk.CellRendererText()
        self.activityCell.connect('edited', self.activity_name_edited_cb, self.activity_store)
        self.activityColumn.pack_start(self.activityCell, True)
        self.activityColumn.set_attributes(self.activityCell, text = 1)
        self.activityColumn.set_sort_column_id(1)
        self.activity_tree.append_column(self.activityColumn)

        self.activity_tree.set_model(self.activity_store)

        self.selection = self.activity_tree.get_selection()
        self.selection.connect('changed', self.activity_changed, self.activity_store)


        # create and fill category tree
        self.category_tree = self.get_widget('category_list')
        self.get_widget("categories_label").set_mnemonic_widget(self.category_tree)
        self.category_store = CategoryStore()

        self.categoryColumn = gtk.TreeViewColumn(_("Category"))
        self.categoryColumn.set_expand(True)
        self.categoryCell = gtk.CellRendererText()
        self.categoryCell.connect('edited', self.category_edited_cb, self.category_store)

        self.categoryColumn.pack_start(self.categoryCell, True)
        self.categoryColumn.set_attributes(self.categoryCell, text = 1)
        self.categoryColumn.set_sort_column_id(1)
        self.categoryColumn.set_cell_data_func(self.categoryCell, self.unsorted_painter)
        self.category_tree.append_column(self.categoryColumn)

        self.category_store.load()
        self.category_tree.set_model(self.category_store)

        selection = self.category_tree.get_selection()
        selection.connect('changed', self.category_changed_cb, self.category_store)

        self.load_config()

        self._gui.connect_signals(self)

        # Allow enable drag and drop of rows including row move
        self.activity_tree.enable_model_drag_source( gtk.gdk.BUTTON1_MASK,
                                                self.TARGETS,
                                                gtk.gdk.ACTION_DEFAULT|
                                                gtk.gdk.ACTION_MOVE)
        self.activity_tree.enable_model_drag_dest(self.TARGETS,
                                                  gtk.gdk.ACTION_MOVE)

        self.category_tree.enable_model_drag_dest(self.TARGETS,
                                                  gtk.gdk.ACTION_MOVE)

        self.activity_tree.connect("drag_data_get", self.drag_data_get_data)
        self.activity_tree.connect("drag_data_received",
                                   self.drag_data_received_data)

        self.category_tree.connect("drag_data_received",
                                   self.on_category_drop)

        #select first category
        selection = self.category_tree.get_selection()
        selection.select_path((0,))
        
        self.prev_selected_activity = None
        self.prev_selected_category = None
        
        # disable notification thing if pynotify is not available
        try:
            import pynotify
        except:
            self.get_widget("notification_preference_frame").hide()


    def load_config(self):
        self.get_widget("shutdown_track").set_active(self.config.get_stop_on_shutdown())
        self.get_widget("idle_track").set_active(self.config.get_timeout_enabled())
        self.get_widget("notify_interval").set_value(self.config.get_notify_interval())
        self.get_widget("keybinding").set_text(self.config.get_keybinding())
        self.get_widget("notify_on_idle").set_active(self.config.get_notify_on_idle())


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
                
    def select_category(self, id):
        model = self.category_tree.get_model()
        i = 0
        for row in model:
            if row[0] == id:
                self.category_tree.set_cursor((i, ))
            i += 1
                
    def on_activity_list_drag_motion(self, treeview, drag_context, x, y, eventtime):
        self.prev_selected_activity = None
        try:
            target_path, drop_position = treeview.get_dest_row_at_pos(x, y)
            model, source = treeview.get_selection().get_selected()

        except:
            return

        drop_yes = ("drop_yes", gtk.TARGET_SAME_APP, 0)
        drop_no = ("drop_no", gtk.TARGET_SAME_APP, 0)

        if drop_position == gtk.TREE_VIEW_DROP_AFTER or \
           drop_position == gtk.TREE_VIEW_DROP_BEFORE:
            treeview.enable_model_drag_dest(self.TARGETS, gtk.gdk.ACTION_MOVE)
        else:
            treeview.enable_model_drag_dest([drop_no], gtk.gdk.ACTION_MOVE)


    def on_category_list_drag_motion(self, treeview, drag_context, x, y, eventtime):
        self.prev_selected_category = None
        try:
            target_path, drop_position = treeview.get_dest_row_at_pos(x, y)
            model, source = treeview.get_selection().get_selected()

        except:
            return

        drop_yes = ("drop_yes", gtk.TARGET_SAME_APP, 0)
        drop_no = ("drop_no", gtk.TARGET_SAME_APP, 0)

        if drop_position != gtk.TREE_VIEW_DROP_AFTER and \
           drop_position != gtk.TREE_VIEW_DROP_BEFORE:
            treeview.enable_model_drag_dest(self.TARGETS, gtk.gdk.ACTION_MOVE)
        else:
            treeview.enable_model_drag_dest([drop_no], gtk.gdk.ACTION_MOVE)

          
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
                print "insert '%s' before '%s'" % (data, model[iter][3])
                storage.move_activity(int(data), model[iter][3], insert_after = False)
            else:
                print "insert '%s' after '%s'" % (data, model[iter][3])
                storage.move_activity(int(data), model[iter][3], insert_after = True)
        else:
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
            changed = storage.change_category(int(data), model[iter][0])
            
            context.finish(changed, True, etime)
        else:
            context.finish(False, True, etime)

        return




    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def get_store(self):
        """returns store, so we can add some watchers in case if anything changes"""
        return self.activity_store

    def show(self):
        self.window.show_all()

    # callbacks
    def category_edited_cb(self, cell, path, new_text, model):
        id = model[path][0]
        if id == -1:
            return False #ignoring unsorted category

        #look for dupes
        categories = storage.get_category_list()
        for category in categories:
            if category['name'].lower() == new_text.lower():
                if id == -2: # that was a new category
                    self.category_store.remove(model.get_iter(path))
                self.select_category(category['id'])
                return False

        if id == -2: #new category
            id = storage.add_category(new_text.decode("utf-8"))
            model[path][0] = id
        else:
            storage.update_category(id, new_text)

        model[path][1] = new_text


    def activity_name_edited_cb(self, cell, path, new_text, model):
        id = model[path][0]
        category_id = model[path][2]
        
        #look for dupes
        activities = storage.get_activities(category_id)
        for activity in activities:
            if activity['name'].lower() == new_text.lower():
                if id == -1: # that was a new category
                    self.activity_store.remove(model.get_iter(path))
                self.select_activity(activity['id'])
                return False
        
        model[path][0] = storage.add_activity(new_text.decode("utf-8"), category_id)
        model[path][1] = new_text
        return True
        

    def category_changed_cb(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()
        id = 0
        if iter == None:
            self.activity_store.clear()
        else:
            self.prev_selected_activity = None

            id = model[iter][0]
            self.activity_store.load(model[iter][0])
        
        #start with nothing
        self.get_widget('activity_up').set_sensitive(False)
        self.get_widget('activity_down').set_sensitive(False)
        self.get_widget('activity_edit').set_sensitive(False)
        self.get_widget('activity_remove').set_sensitive(False)

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
        unsorted_selected = self._get_selected_category() == -1
        self.get_widget('activity_up').set_sensitive(False)
        self.get_widget('activity_down').set_sensitive(False)

        self.get_widget('activity_edit').set_sensitive(iter != None)
        self.get_widget('activity_remove').set_sensitive(iter != None)
        
        if iter != None and not unsorted_selected:
            first_item = model.get_path(iter) == (0,)
            self.get_widget('activity_up').set_sensitive(not first_item)

            last_item = model.iter_next(iter) == None
            self.get_widget('activity_down').set_sensitive(not last_item)

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
        
    def unsorted_painter(self, column, cell, model, iter):
        cell_id = model.get_value(iter, 0)
        cell_text = model.get_value(iter, 1)
        if cell_id == -1:
            text = '<span color="#555" style="italic">%s</span>' % cell_text # TODO - should get color from theme
            cell.set_property('markup', text)
        else:
            cell.set_property('text', cell_text)
            
        return

    def on_activity_list_button_pressed(self, tree, event):
        self.activityCell.set_property("editable", False)
        

    def on_activity_list_button_released(self, tree, event):
        if event.button == 1 and tree.get_path_at_pos(int(event.x), int(event.y)):
            # Get treeview path.
            path, column, x, y = tree.get_path_at_pos(int(event.x), int(event.y))

            if self.prev_selected_activity == path:
                self.activityCell.set_property("editable", True)
                tree.set_cursor(path, focus_column = self.activityColumn, start_editing = True)
    
            self.prev_selected_activity = path
        
    def on_category_list_button_pressed(self, tree, event):
        self.activityCell.set_property("editable", False)
        
    def on_category_list_button_released(self, tree, event):
        if event.button == 1 and tree.get_path_at_pos(int(event.x), int(event.y)):
            # Get treeview path.
            path, column, x, y = tree.get_path_at_pos(int(event.x), int(event.y))

            if self.prev_selected_category == path and \
               self._get_selected_category() != -1: #do not allow to edit unsorted
                self.categoryCell.set_property("editable", True)
                tree.set_cursor(path, focus_column = self.categoryColumn, start_editing = True)
            else:
                self.categoryCell.set_property("editable", False)
            

            self.prev_selected_category = path
        

    def on_activity_remove_clicked(self, button):
        self.remove_current_activity()

    def on_activity_edit_clicked(self, button):
        self.activityCell.set_property("editable", True)

        selection = self.activity_tree.get_selection()
        (model, iter) = selection.get_selected()
        path = model.get_path(iter)[0]
        self.activity_tree.set_cursor(path, focus_column = self.activityColumn, start_editing = True)
        


    """keyboard events"""
    def on_activity_list_key_pressed(self, tree, event_key):
        key = event_key.keyval
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()
        if (event_key.keyval == gtk.keysyms.Delete):
            self.remove_current_activity()

        elif key == gtk.keysyms.F2 :
            self.activityCell.set_property("editable", True)
            path = model.get_path(iter)[0]
            tree.set_cursor(path, focus_column = self.activityColumn, start_editing = True)
            #tree.grab_focus()
            #tree.set_cursor(path, start_editing = True)

    def remove_current_activity(self):
        selection = self.activity_tree.get_selection()
        (model, iter) = selection.get_selected()
        storage.remove_activity(model[iter][0])
        self._del_selected_row(self.activity_tree)


    def on_category_remove_clicked(self, button):
        self.remove_current_category()
        
    def on_category_edit_clicked(self, button):
        self.categoryCell.set_property("editable", True)

        selection = self.category_tree.get_selection()
        (model, iter) = selection.get_selected()
        path = model.get_path(iter)[0]
        self.category_tree.set_cursor(path, focus_column = self.categoryColumn, start_editing = True)
        
        
    def on_category_list_key_pressed(self, tree, event_key):
        key = event_key.keyval
        
        if self._get_selected_category() == -1:
            return #ignoring unsorted category
        
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()

        if  key == gtk.keysyms.Delete:
            self.remove_current_category()
        elif key == gtk.keysyms.F2:
            self.categoryCell.set_property("editable", True)
            path = model.get_path(iter)[0]
            tree.set_cursor(path, focus_column = self.categoryColumn, start_editing = True)
            #tree.grab_focus()
            #tree.set_cursor(path, start_editing = True)

    def remove_current_category(self):
        selection = self.category_tree.get_selection()
        (model, iter) = selection.get_selected()
        id = model[iter][0]
        if id != -1:
            storage.remove_category(id)
            self._del_selected_row(self.category_tree)

    def on_preferences_window_key_press(self, widget, event):
        # ctrl+w means close window
        if (event.keyval == gtk.keysyms.w \
            and event.state & gtk.gdk.CONTROL_MASK):
            self.close_window()

        # escape can mean several things
        if event.keyval == gtk.keysyms.Escape:
            #check, maybe we are editing stuff
            if self.activityCell.get_property("editable"):
                self.activityCell.set_property("editable", False)
                return
            if self.categoryCell.get_property("editable"):
                self.categoryCell.set_property("editable", False)
                return

            self.close_window()     

    """button events"""
    def on_category_add_clicked(self, button):
        """ appends row, jumps to it and allows user to input name """
        
        new_category = self.category_store.insert_before(self.category_store.unsorted_category,
                                                         [-2, _(u"New category"), -1])

        self.categoryCell.set_property("editable", True)
        self.category_tree.set_cursor_on_cell((len(self.category_tree.get_model()) - 2, ),
                                         focus_column = self.category_tree.get_column(0),
                                         focus_cell = None,
                                         start_editing = True)


    def on_activity_add_clicked(self, button):
        """ appends row, jumps to it and allows user to input name """
        category_id = self._get_selected_category()
        
        new_activity = self.activity_store.append([-1, _(u"New activity"), category_id, -1])

        (model, iter) = self.selection.get_selected()

        self.activityCell.set_property("editable", True)
        self.activity_tree.set_cursor_on_cell(model.get_string_from_iter(new_activity),
                                         focus_column = self.activity_tree.get_column(0),
                                         focus_cell = None,
                                         start_editing = True)

    def on_activity_remove_clicked(self, button):
        removable_id = self._del_selected_row(self.activity_tree)
        storage.remove_activity(removable_id)

    def on_activity_up_clicked(self, button):
        (model, iter) = self.selection.get_selected()

        #previous item
        prev_iter = get_prev(self.selection, model)
        storage.swap_activities(model[iter][0], model[iter][3],
                                model[prev_iter][0], model[prev_iter][3])
        model.move_before(iter, prev_iter)

        self.activity_changed(self.selection, model)

    def on_activity_down_clicked(self, button):
        (model, iter) = self.selection.get_selected()

        next_iter = model.iter_next(iter)
        storage.swap_activities(model[iter][0], model[iter][3],
                                model[next_iter][0], model[next_iter][3])
        self.activity_store.move_after(iter, next_iter)

        self.activity_changed(self.selection, model)

    def on_close_button_clicked(self, button):
        self.close_window()

    def on_close(self, widget, event):
        self.close_window()        
    
    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            return False

    def on_shutdown_track_toggled(self, checkbox):
        self.config.set_stop_on_shutdown(checkbox.get_active())

    def on_idle_track_toggled(self, checkbox):
        self.config.set_timeout_enabled(checkbox.get_active())

    def on_notify_on_idle_toggled(self, checkbox):
        self.config.set_notify_on_idle(checkbox.get_active())

    def on_notify_interval_format_value(self, slider, value):
        if value <=120:
            # notify interval slider value label
            label = _(u"%(interval_minutes)d minutes") % {'interval_minutes': value}
        else:
            # notify interval slider value label
            label = _(u"Never")
        
        return label
    
    def on_notify_interval_value_changed(self, scale):
        value = int(scale.get_value())
        self.config.set_notify_interval(value)
        self.get_widget("notify_on_idle").set_sensitive(value <= 120)
    
    def on_keybinding_changed(self, textbox):
        self.config.set_keybinding(textbox.get_text())

    def on_preferences_window_destroy(self, window):
        self.window = None
        
