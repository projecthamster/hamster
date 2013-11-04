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

import logging
import pygtk
pygtk.require('2.0')

import os
import gobject
import gtk

import datetime as dt

try:
    import wnck
except:
    wnck = None

try:
    import appindicator
except:
    appindicator = None


from gettext import ngettext

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


class WorkspaceStore(gtk.ListStore):
    def __init__(self):
        #id, name, color_code, order
        gtk.ListStore.__init__(self, int, gobject.TYPE_PYOBJECT, str)

formats = ["fixed", "symbolic", "minutes"]
appearances = ["text", "icon", "both"]

from configuration import runtime, conf, load_ui_file
import widgets
from lib import stuff, trophies



class PreferencesEditor(gtk.Object):
    TARGETS = [
        ('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_WIDGET, 0),
        ('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_APP, 0),
        ]


    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, parent = None):
        gtk.Object.__init__(self)
        self.parent = parent
        self._gui = load_ui_file("preferences.ui")
        self.window = self.get_widget('preferences_window')
        self.window.connect("delete_event", self.on_delete_window)

        # Translators: 'None' refers here to the Todo list choice in Hamster preferences (Tracking tab)
        self.activities_sources = [("", _("None")),
                                   ("evo", "Evolution"),
                                   ("gtg", "Getting Things Gnome"),
                                   ("rt", "Request Tracker"),
                                   ("redmine", "Redmine")]
        self.todo_combo = gtk.combo_box_new_text()
        for code, label in self.activities_sources:
            self.todo_combo.append_text(label)
        self.todo_combo.connect("changed", self.on_todo_combo_changed)
        self.get_widget("todo_pick").add(self.todo_combo)

        # RT prefs
        self.rt_url = gtk.Entry()
        self.rt_url.connect("changed", self.on_rt_url_changed)
        self.get_widget('rt_url').add(self.rt_url)
        
        self.rt_user = gtk.Entry()
        self.rt_user.connect("changed", self.on_rt_user_changed)
        self.get_widget('rt_user').add(self.rt_user)
        
        self.rt_pass = gtk.Entry()
        self.rt_pass.set_visibility(False)
        self.rt_pass.connect("changed", self.on_rt_pass_changed)
        self.get_widget('rt_pass').add(self.rt_pass)
        
        self.rt_query = gtk.Entry()
        self.rt_query.connect("changed", self.on_rt_query_changed)
        self.get_widget('rt_query').add(self.rt_query)

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

        self.day_start = widgets.TimeInput(dt.time(5,30))
        self.get_widget("day_start_placeholder").add(self.day_start)


        self.load_config()

        # Allow enable drag and drop of rows including row move
        self.activity_tree.enable_model_drag_source( gtk.gdk.BUTTON1_MASK,
                                                self.TARGETS,
                                                gtk.gdk.ACTION_DEFAULT|
                                                gtk.gdk.ACTION_MOVE)

        self.category_tree.enable_model_drag_dest(self.TARGETS,
                                                  gtk.gdk.ACTION_MOVE)

        self.activity_tree.connect("drag_data_get", self.drag_data_get_data)

        self.category_tree.connect("drag_data_received", self.on_category_drop)

        #select first category
        selection = self.category_tree.get_selection()
        selection.select_path((0,))

        self.prev_selected_activity = None
        self.prev_selected_category = None


        # create and fill workspace tree
        self.workspace_tree = self.get_widget('workspace_list')
        self.workspace_store = WorkspaceStore()

        self.wNameColumn = gtk.TreeViewColumn(_("Name"))
        self.wNameColumn.set_expand(True)
        self.wNameCell = gtk.CellRendererText()
        self.wNameCell.set_property('editable', False)
        self.wActivityColumn = gtk.TreeViewColumn(_("Activity"))
        self.wActivityColumn.set_expand(True)
        self.wActivityCell = gtk.CellRendererText()
        self.wActivityCell.set_property('editable', True)

        self.external_listeners.extend([
            (self.wActivityCell, self.wActivityCell.connect('edited', self.on_workspace_activity_edited))
        ])

        self.wNameColumn.pack_start(self.wNameCell, True)
        self.wNameColumn.set_attributes(self.wNameCell)
        self.wNameColumn.set_sort_column_id(1)
        self.wNameColumn.set_cell_data_func(self.wNameCell, self.workspace_name_celldata)
        self.workspace_tree.append_column(self.wNameColumn)
        self.wActivityColumn.pack_start(self.wActivityCell, True)
        self.wActivityColumn.set_attributes(self.wActivityCell, text=2)
        self.wActivityColumn.set_sort_column_id(1)
        self.workspace_tree.append_column(self.wActivityColumn)

        self.workspace_tree.set_model(self.workspace_store)

        # disable notification thing if pynotify is not available
        try:
            import pynotify
        except:
            self.get_widget("notification_preference_frame").hide()


        self.external_listeners.extend([
            (self.day_start, self.day_start.connect("time-entered", self.on_day_start_changed))
        ])

        # disable workspace tracking if wnck is not there
        if wnck:
            self.screen = wnck.screen_get_default()
            for workspace in self.screen.get_workspaces():
                self.on_workspace_created(self.screen, workspace)

            self.external_listeners.extend([
                (self.screen, self.screen.connect("workspace-created", self.on_workspace_created)),
                (self.screen, self.screen.connect("workspace-destroyed", self.on_workspace_deleted))
            ])
        else:
            self.get_widget("workspace_tab").hide()
        
        if not appindicator:
            self.get_widget("tray_tab").hide()

        self._gui.connect_signals(self)
        self.show()


    def show(self):
        self.get_widget("notebook1").set_current_page(0)
        self.window.show_all()

    def on_rt_url_changed(self, entry):
        conf.set('rt_url', self.rt_url.get_text())

    def on_rt_user_changed(self, entry):
        conf.set('rt_user', self.rt_user.get_text())

    def on_rt_pass_changed(self, entry):
        conf.set('rt_pass', self.rt_pass.get_text())

    def on_rt_query_changed(self, entry):
        conf.set('rt_query', self.rt_query.get_text())

    def on_todo_combo_changed(self, combo):
        conf.set("activities_source", self.activities_sources[combo.get_active()][0])

    def workspace_name_celldata(self, column, cell, model, iter, user_data=None):
        name = model.get_value(iter, 1).get_name()
        cell.set_property('text', str(name))

    def on_workspace_created(self, screen, workspace, user_data=None):
        workspace_number = workspace.get_number()
        activity = ""
        if workspace_number < len(self.workspace_mapping):
            activity = self.workspace_mapping[workspace_number]

        self.workspace_store.append([workspace_number, workspace, activity])

    def on_workspace_deleted(self, screen, workspace, user_data=None):
        row = self.workspace_store.get_iter_first()
        while row:
            if self.workspace_store.get_value(row, 1) == workspace:
                if not self.workspace_store.remove(row):
                    # row is now invalid, stop iteration
                    break
            else:
                row = self.workspace_store.iter_next(row)

    def on_workspace_activity_edited(self, cell, path, value):
        index = int(path)
        while index >= len(self.workspace_mapping):
            self.workspace_mapping.append("")

        value = value.decode("utf8", "replace")
        self.workspace_mapping[index] = value
        conf.set("workspace_mapping", self.workspace_mapping)
        self.workspace_store[path][2] = value

    def load_config(self, *args):
        self.get_widget("shutdown_track").set_active(conf.get("stop_on_shutdown"))
        self.get_widget("idle_track").set_active(conf.get("enable_timeout"))
        self.get_widget("notify_interval").set_value(conf.get("notify_interval"))

        self.get_widget("notify_on_idle").set_active(conf.get("notify_on_idle"))
        self.get_widget("notify_on_idle").set_sensitive(conf.get("notify_interval") <=120)

        self.get_widget("workspace_tracking_name").set_active("name" in conf.get("workspace_tracking"))
        self.get_widget("workspace_tracking_memory").set_active("memory" in conf.get("workspace_tracking"))

        day_start = conf.get("day_start_minutes")
        day_start = dt.time(day_start / 60, day_start % 60)
        self.day_start.set_time(day_start)

        self.tags = [tag["name"] for tag in runtime.storage.get_tags(only_autocomplete=True)]
        self.get_widget("autocomplete_tags").set_text(", ".join(self.tags))

        self.workspace_mapping = conf.get("workspace_mapping")
        self.get_widget("workspace_list").set_sensitive(self.get_widget("workspace_tracking_name").get_active())


        current_source = conf.get("activities_source")
        for i, (code, label) in enumerate(self.activities_sources):
            if code == current_source:
                self.todo_combo.set_active(i)
        
        self.rt_url.set_text(conf.get('rt_url'))
        self.rt_user.set_text(conf.get('rt_user'))
        self.rt_pass.set_text(conf.get('rt_pass'))
        self.rt_query.set_text(conf.get('rt_query'))
        
        self.get_widget("icon_glow").set_active(conf.get("icon_glow"))
        self.get_widget("show_label").set_active(conf.get("show_label"))
        self.get_widget("label_length").set_sensitive(conf.get("show_label"))
        self.get_widget("label_length").set_value(conf.get("label_length"))
        self.get_widget("last_activities_days").set_value(conf.get("last_activities_days"))
        self.get_widget("rt_activities_only").set_active(conf.get("rt_activities_only"))


    def on_autocomplete_tags_view_focus_out_event(self, view, event):
        buf = self.get_widget("autocomplete_tags")
        updated_tags = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), 0) \
                          .decode("utf-8")
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
            model, source = view.get_selection().get_selected()

        except:
            return

        drop_yes = ("drop_yes", gtk.TARGET_SAME_APP, 0)
        drop_no = ("drop_no", gtk.TARGET_SAME_APP, 0)

        if drop_position != gtk.TREE_VIEW_DROP_AFTER and \
           drop_position != gtk.TREE_VIEW_DROP_BEFORE:
            treeview.enable_model_drag_dest(self.TARGETS, gtk.gdk.ACTION_MOVE)
        else:
            treeview.enable_model_drag_dest([drop_no], gtk.gdk.ACTION_MOVE)



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


    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def get_store(self):
        """returns store, so we can add some watchers in case if anything changes"""
        return self.activity_store


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
            id = runtime.storage.add_category(new_text.decode("utf-8"))
            model[path][0] = id
        else:
            runtime.storage.update_category(id, new_text.decode("utf-8"))

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
            model[path][0] = runtime.storage.add_activity(new_text.decode("utf-8"), category_id)
        else: #existing activity -> update
            new = new_text.decode("utf-8")
            runtime.storage.update_activity(id, new, category_id)
            # size matters - when editing activity name just changed the case (bar -> Bar)
            if prev != new and prev.lower() == new.lower():
                trophies.unlock("size_matters")

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

        if iter:
            return model[iter][0]
        else:
            return None


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
            # Get view path.
            path, column, x, y = tree.get_path_at_pos(int(event.x), int(event.y))

            if self.prev_selected_activity == path:
                self.activityCell.set_property("editable", True)
                tree.set_cursor(path, focus_column = self.activityColumn, start_editing = True)

            self.prev_selected_activity = path

    def on_category_list_button_pressed(self, tree, event):
        self.activityCell.set_property("editable", False)

    def on_category_list_button_released(self, tree, event):
        if event.button == 1 and tree.get_path_at_pos(int(event.x), int(event.y)):
            # Get view path.
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
        runtime.storage.remove_activity(model[iter][0])
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
            runtime.storage.remove_category(id)
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
                                                         [-2, _(u"New category")])

        self.categoryCell.set_property("editable", True)
        self.category_tree.set_cursor_on_cell((len(self.category_tree.get_model()) - 2, ),
                                         focus_column = self.category_tree.get_column(0),
                                         focus_cell = None,
                                         start_editing = True)


    def on_activity_add_clicked(self, button):
        """ appends row, jumps to it and allows user to input name """
        category_id = self._get_selected_category()

        new_activity = self.activity_store.append([-1, _(u"New activity"), category_id])

        (model, iter) = self.selection.get_selected()

        self.activityCell.set_property("editable", True)
        self.activity_tree.set_cursor_on_cell(model.get_string_from_iter(new_activity),
                                         focus_column = self.activity_tree.get_column(0),
                                         focus_cell = None,
                                         start_editing = True)

    def on_activity_remove_clicked(self, button):
        removable_id = self._del_selected_row(self.activity_tree)
        runtime.storage.remove_activity(removable_id)


    def on_close_button_clicked(self, button):
        self.close_window()

    def on_close(self, widget, event):
        self.close_window()

    def on_delete_window(self, window, event):
        self.close_window()
        return True

    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            for obj, handler in self.external_listeners:
                obj.disconnect(handler)
            self.window.destroy()
            self.window = None
            self._gui = None
            self.wNameColumn = None
            self.categoryColumn = None
            self.emit("on-close")

    def on_workspace_tracking_toggled(self, checkbox):
        workspace_tracking = []
        self.get_widget("workspace_list").set_sensitive(self.get_widget("workspace_tracking_name").get_active())
        if self.get_widget("workspace_tracking_name").get_active():
            workspace_tracking.append("name")

        if self.get_widget("workspace_tracking_memory").get_active():
            workspace_tracking.append("memory")

        conf.set("workspace_tracking", workspace_tracking)

    def on_shutdown_track_toggled(self, checkbox):
        conf.set("stop_on_shutdown", checkbox.get_active())

    def on_idle_track_toggled(self, checkbox):
        conf.set("enable_timeout", checkbox.get_active())

    def on_notify_on_idle_toggled(self, checkbox):
        conf.set("notify_on_idle", checkbox.get_active())

    def on_rt_activities_only_toggled(self, checkbox):
        conf.set('rt_activities_only', checkbox.get_active())

    def on_notify_interval_format_value(self, slider, value):
        if value <=120:
            # notify interval slider value label
            label = ngettext("%(interval_minutes)d minute",
                             "%(interval_minutes)d minutes",
                             value) % {'interval_minutes': value}
        else:
            # notify interval slider value label
            label = _(u"Never")

        return label

    def on_notify_interval_value_changed(self, scale):
        value = int(scale.get_value())
        conf.set("notify_interval", value)
        self.get_widget("notify_on_idle").set_sensitive(value <= 120)

    def on_day_start_changed(self, widget):
        day_start = self.day_start.get_time()
        if day_start is None:
            return

        day_start = day_start.hour * 60 + day_start.minute

        conf.set("day_start_minutes", day_start)
        
    def on_icon_glow_toggled(self, checkbox):
        conf.set("icon_glow", checkbox.get_active())
        
    def on_show_label_toggled(self, checkbox):
        show_label = checkbox.get_active()
        conf.set("show_label", show_label)
        self.get_widget("label_length").set_sensitive(show_label)
        
    def on_label_length_value_changed(self, scale):
        value = int(scale.get_value())
        conf.set("label_length", value)
        
    def on_last_activities_days_value_changed(self, scale):
        value = int(scale.get_value())
        conf.set("last_activities_days", value)

    def on_preferences_window_destroy(self, window):
        self.window = None
    
