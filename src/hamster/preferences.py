# -*- coding: utf-8 -*-

# Copyright (C) 2007, 2008, 2014 Toms Bauģis <toms.baugis at gmail.com>

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

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from hamster import widgets
from hamster.lib import datetime as dt
from hamster.lib import stuff
from hamster.lib.configuration import Controller, runtime, conf


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
        gtk.ListStore.__init__(self, int, str)

    def load(self):
        category_list = runtime.storage.get_categories()

        for category in category_list:
            self.append([category['id'], category['name']])

        self.unsorted_category = self.append([-1, _("Unsorted")]) # all activities without category


class ActivityStore(gtk.ListStore):
    def __init__(self):
        #id, name, category_id, order
        gtk.ListStore.__init__(self, int, str, int)

    def load(self, category_id):
        self.clear()

        if category_id is None:
            return

        activity_list = runtime.storage.get_category_activities(category_id)

        for activity in activity_list:
            self.append([activity['id'],
                         activity['name'],
                         activity['category_id']])


class PreferencesEditor(Controller):
    TARGETS = [
        ('MY_TREE_MODEL_ROW', gtk.TargetFlags.SAME_WIDGET, 0),
        ('MY_TREE_MODEL_ROW', gtk.TargetFlags.SAME_APP, 0),
        ]

    def __init__(self):
        Controller.__init__(self, ui_file="preferences.ui")

        # create and fill activity tree
        self.activity_tree = self.get_widget('activity_list')
        self.get_widget("activities_label").set_mnemonic_widget(self.activity_tree)
        self.activity_store = ActivityStore()

        self.external_listeners = []

        self.activityColumn = gtk.TreeViewColumn(_("Name"))
        self.activityColumn.set_expand(True)
        self.activityCell = gtk.CellRendererText()
        self.external_listeners.extend([
            (self.activityCell, self.activityCell.connect('edited', self.activity_name_edited_cb, self.activity_store))
        ])
        self.activityColumn.pack_start(self.activityCell, True)
        self.activityColumn.set_attributes(self.activityCell, text=1)
        self.activityColumn.set_sort_column_id(1)
        self.activity_tree.append_column(self.activityColumn)

        self.activity_tree.set_model(self.activity_store)

        self.selection = self.activity_tree.get_selection()

        self.external_listeners.extend([
            (self.selection, self.selection.connect('changed', self.activity_changed, self.activity_store))
        ])

        # create and fill category tree
        self.category_tree = self.get_widget('category_list')
        self.get_widget("categories_label").set_mnemonic_widget(self.category_tree)
        self.category_store = CategoryStore()

        self.categoryColumn = gtk.TreeViewColumn(_("Category"))
        self.categoryColumn.set_expand(True)
        self.categoryCell = gtk.CellRendererText()

        self.external_listeners.extend([
            (self.categoryCell, self.categoryCell.connect('edited', self.category_edited_cb, self.category_store))
        ])

        self.categoryColumn.pack_start(self.categoryCell, True)
        self.categoryColumn.set_attributes(self.categoryCell, text=1)
        self.categoryColumn.set_sort_column_id(1)
        self.categoryColumn.set_cell_data_func(self.categoryCell, self.unsorted_painter)
        self.category_tree.append_column(self.categoryColumn)

        self.category_store.load()
        self.category_tree.set_model(self.category_store)

        selection = self.category_tree.get_selection()
        self.external_listeners.extend([
            (selection, selection.connect('changed', self.category_changed_cb, self.category_store))
        ])

        self.day_start = widgets.TimeInput(dt.time(5,30), parent=self.get_widget("day_start_placeholder"))

        self.load_config()

        # Allow enable drag and drop of rows including row move
        self.activity_tree.enable_model_drag_source(gdk.ModifierType.BUTTON1_MASK,
                                                    self.TARGETS,
                                                    gdk.DragAction.DEFAULT|
                                                    gdk.DragAction.MOVE)

        self.category_tree.enable_model_drag_dest(self.TARGETS,
                                                  gdk.DragAction.MOVE)

        self.activity_tree.connect("drag_data_get", self.drag_data_get_data)

        self.category_tree.connect("drag_data_received", self.on_category_drop)

        #select first category
        selection = self.category_tree.get_selection()
        selection.select_path((0,))

        self.prev_selected_activity = None
        self.prev_selected_category = None

        self.external_listeners.extend([
            (self.day_start, self.day_start.connect("time-entered", self.on_day_start_changed))
        ])

        self.show()

    def show(self):
        self.get_widget("notebook1").set_current_page(0)
        self.window.show_all()

    def load_config(self, *args):
        conf.bind("stop-on-shutdown", self.get_widget("shutdown_track"), "active")

        self.day_start.time = conf.day_start

        self.tags = [tag["name"] for tag in runtime.storage.get_tags(only_autocomplete=True)]
        self.get_widget("autocomplete_tags").set_text(", ".join(self.tags))

    def on_autocomplete_tags_view_focus_out_event(self, view, event):
        buf = self.get_widget("autocomplete_tags")
        updated_tags = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), 0)
        if updated_tags == self.tags:
            return

        self.tags = updated_tags

        runtime.storage.update_autocomplete_tags(updated_tags)

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

    def on_category_list_drag_motion(self, treeview, drag_context, x, y, eventtime):
        self.prev_selected_category = None
        try:
            target_path, drop_position = treeview.get_dest_row_at_pos(x, y)
            model, source = treeview.get_selection().get_selected()

        except:
            return

        drop_yes = ("drop_yes", gtk.TargetFlags.SAME_APP, 0)
        drop_no = ("drop_no", gtk.TargetFlags.SAME_APP, 0)

        if drop_position != gtk.TREE_VIEW_DROP_AFTER and \
           drop_position != gtk.TREE_VIEW_DROP_BEFORE:
            treeview.enable_model_drag_dest(self.TARGETS, gdk.DragAction.MOVE)
        else:
            treeview.enable_model_drag_dest([drop_no], gdk.DragAction.MOVE)

    def on_category_drop(self, treeview, context, x, y, selection,
                                info, etime):
        model = self.category_tree.get_model()
        data = selection.data
        drop_info = treeview.get_dest_row_at_pos(x, y)

        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            changed = runtime.storage.change_category(int(data), model[iter][0])

            context.finish(changed, True, etime)
        else:
            context.finish(False, True, etime)

        return

    # callbacks
    def category_edited_cb(self, cell, path, new_text, model):
        id = model[path][0]
        if id == -1:
            return False #ignoring unsorted category

        #look for dupes
        categories = runtime.storage.get_categories()
        for category in categories:
            if category['name'].lower() == new_text.lower():
                if id == -2: # that was a new category
                    self.category_store.remove(model.get_iter(path))
                self.select_category(category['id'])
                return False

        if id == -2: #new category
            id = runtime.storage.add_category(new_text)
            model[path][0] = id
        else:
            runtime.storage.update_category(id, new_text)

        model[path][1] = new_text

    def activity_name_edited_cb(self, cell, path, new_text, model):
        id = model[path][0]
        category_id = model[path][2]

        activities = runtime.storage.get_category_activities(category_id)
        prev = None
        for activity in activities:
            if id == activity['id']:
                prev = activity['name']
            else:
                # avoid two activities in same category with same name
                if activity['name'].lower() == new_text.lower():
                    if id == -1: # that was a new activity
                        self.activity_store.remove(model.get_iter(path))
                    self.select_activity(activity['id'])
                    return False

        if id == -1: #new activity -> add
            model[path][0] = runtime.storage.add_activity(new_text, category_id)
        else: #existing activity -> update
            new = new_text
            runtime.storage.update_activity(id, new, category_id)

        model[path][1] = new_text
        return True

    def category_changed_cb(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()
        id = 0
        if iter is None:
            self.activity_store.clear()
        else:
            self.prev_selected_activity = None

            id = model[iter][0]
            self.activity_store.load(model[iter][0])

        #start with nothing
        self.get_widget('activity_edit').set_sensitive(False)
        self.get_widget('activity_remove').set_sensitive(False)

        return True

    def _get_selected_category(self):
        selection = self.get_widget('category_list').get_selection()
        (model, iter) = selection.get_selected()

        return model[iter][0] if iter else None

    def activity_changed(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()

        # treat any selected case
        unsorted_selected = self._get_selected_category() == -1
        self.get_widget('activity_edit').set_sensitive(iter != None)
        self.get_widget('activity_remove').set_sensitive(iter != None)

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

    def unsorted_painter(self, column, cell, model, iter, data):
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
                tree.set_cursor_on_cell(path, self.activityColumn, self.activityCell, True)

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
                tree.set_cursor_on_cell(path, self.categoryColumn, self.categoryCell, True)
            else:
                self.categoryCell.set_property("editable", False)


            self.prev_selected_category = path

    def on_activity_remove_clicked(self, button):
        self.remove_current_activity()

    def on_activity_edit_clicked(self, button):
        self.activityCell.set_property("editable", True)

        selection = self.activity_tree.get_selection()
        (model, iter) = selection.get_selected()
        path = model.get_path(iter)
        self.activity_tree.set_cursor_on_cell(path, self.activityColumn, self.activityCell, True)

    """keyboard events"""
    def on_activity_list_key_pressed(self, tree, event_key):
        key = event_key.keyval
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()
        if (event_key.keyval == gdk.KEY_Delete):
            self.remove_current_activity()

        elif key == gdk.KEY_F2 :
            self.activityCell.set_property("editable", True)
            path = model.get_path(iter)
            tree.set_cursor_on_cell(path, self.activityColumn, self.activityCell, True)

    def remove_current_activity(self):
        selection = self.activity_tree.get_selection()
        (model, iter) = selection.get_selected()
        runtime.storage.remove_activity(model[iter][0])
        self._del_selected_row(self.activity_tree)

    def on_category_remove_clicked(self, button):
        self.remove_current_category()

    def on_category_edit_clicked(self, button):
        self.categoryCell.set_property("editable", True)

        selection = self.category_tree.get_selection()
        (model, iter) = selection.get_selected()
        path = model.get_path(iter)
        self.category_tree.set_cursor_on_cell(path, self.categoryColumn, self.categoryCell, True)

    def on_category_list_key_pressed(self, tree, event_key):
        key = event_key.keyval

        if self._get_selected_category() == -1:
            return #ignoring unsorted category

        selection = tree.get_selection()
        (model, iter) = selection.get_selected()

        if  key == gdk.KEY_Delete:
            self.remove_current_category()
        elif key == gdk.KEY_F2:
            self.categoryCell.set_property("editable", True)
            path = model.get_path(iter)
            tree.set_cursor_on_cell(path, self.categoryColumn, self.categoryCell, True)

    def remove_current_category(self):
        selection = self.category_tree.get_selection()
        (model, iter) = selection.get_selected()
        id = model[iter][0]
        if id != -1:
            runtime.storage.remove_category(id)
            self._del_selected_row(self.category_tree)

    def on_preferences_window_key_press(self, widget, event):
        # ctrl+w means close window
        if (event.keyval == gdk.KEY_w \
            and event.state & gdk.ModifierType.CONTROL_MASK):
            self.close_window()

        # escape can mean several things
        if event.keyval == gdk.KEY_Escape:
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
                                                         [-2, _("New category")])

        model = self.category_tree.get_model()

        self.categoryCell.set_property("editable", True)
        self.category_tree.set_cursor_on_cell(model.get_path(new_category),
                                         focus_column = self.category_tree.get_column(0),
                                         focus_cell = None,
                                         start_editing = True)

    def on_activity_add_clicked(self, button):
        """ appends row, jumps to it and allows user to input name """
        category_id = self._get_selected_category()

        new_activity = self.activity_store.append([-1, _("New activity"), category_id])

        (model, iter) = self.selection.get_selected()

        self.activityCell.set_property("editable", True)
        self.activity_tree.set_cursor_on_cell(model.get_path(new_activity),
                                              focus_column = self.activity_tree.get_column(0),
                                              focus_cell = None,
                                              start_editing = True)

    def on_activity_remove_clicked(self, button):
        removable_id = self._del_selected_row(self.activity_tree)
        runtime.storage.remove_activity(removable_id)

    def on_day_start_changed(self, widget):
        day_start = self.day_start.time
        if day_start is None:
            return

        day_start = day_start.hour * 60 + day_start.minute
        conf.set("day-start-minutes", day_start)
    def on_close_button_clicked(self, button):
        self.close_window()
