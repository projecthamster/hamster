# - coding: utf-8 -

# Copyright (C) 2007, 2008 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>
# Copyright (C) 2008 Pēteris Caune <cuu508 at gmail.com>

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


import datetime
import os.path
import gnomeapplet, gtk
import gobject

from hamster import dispatcher, storage, SHARED_DATA_DIR
import hamster.eds
from hamster.Configuration import GconfStore

from hamster.stuff import *
from hamster.KeyBinder import *
import idle

class PanelButton(gtk.ToggleButton):
    def __init__(self):
        gtk.ToggleButton.__init__(self)
        self.set_relief(gtk.RELIEF_NONE)
        self.set_border_width(0)
        
        self.label = gtk.Label()
        self.add(self.label)

    def set_text(self, text):
        self.label.set_text(text)

    def get_pos(self):
        return gtk.gdk.Window.get_origin(self.label.window)

    def set_active(self, is_active):
        self.set_property('active', is_active)


class HamsterApplet(object):
    def __init__(self, applet):
        self.config = GconfStore.get_instance()
        
        self.applet = applet
        self.applet.set_applet_flags (gnomeapplet.EXPAND_MINOR);

        self.button = PanelButton()
        
        # load window of activity switcher and todays view
        self.glade = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, "menu.glade"))
        self.window = self.glade.get_widget('hamster-window')
        
        # set up drop down menu
        self.activity_list = self.glade.get_widget('activity-list')
        self.activity_list.set_model(gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT))
        self.activity_list.set_text_column(0)

        # set up autocompletition for the drop-down menu
        self.activities = gtk.ListStore(gobject.TYPE_STRING)
        completion = gtk.EntryCompletion()
        completion.set_model(self.activities)
        completion.set_text_column(0)
        completion.set_minimum_key_length(1)
        self.activity_list.child.set_completion(completion)

        # init today's tree
        self.treeview = self.glade.get_widget('today')
        self.treeview.set_tooltip_column(1)
        
        self.treeview.append_column(gtk.TreeViewColumn("Time", gtk.CellRendererText(), text=2))
        self.treeview.append_column(ExpanderColumn("Name", text = 1))
        self.treeview.append_column(gtk.TreeViewColumn("", gtk.CellRendererText(), text=3))
        
        edit_cell = gtk.CellRendererPixbuf()
        edit_cell.set_property("stock_id", "gtk-edit")
        self.edit_column = gtk.TreeViewColumn("", edit_cell)
        self.treeview.append_column(self.edit_column)


        # Load today's data, activities and set label
        self.last_activity = None
        self.today = datetime.date.today()

        self.load_day()
        self.update_label()

        # refresh hamster every 60 seconds to update duration
        gobject.timeout_add_seconds(60, self.refresh_hamster)

        # build the menu
        self.refresh_menu()

        # remove padding, so we fit on small panels (adapted from clock applet)
        gtk.rc_parse_string ("""style "hamster-applet-button-style" {
                GtkWidget::focus-line-width=0
                GtkWidget::focus-padding=0
            }
                                     
            widget "*.hamster-applet-button" style "hamster-applet-button-style"
        """);
        gtk.Widget.set_name (self.button, "hamster-applet-button");

        self.applet.add(self.button)

        dispatcher.add_handler('panel_visible', self.__show_toggle)
        dispatcher.add_handler('activity_updated', self.after_activity_update)
        dispatcher.add_handler('day_updated', self.after_fact_update)

        self.applet.setup_menu_from_file (
            SHARED_DATA_DIR, "Hamster_Applet.xml",
            None, [
            ("about", self.on_about),
            ("activities", self.on_edit_activities),
            ])

        self.applet.show_all()
        self.applet.set_background_widget(self.applet)

        self.button.connect('toggled', self.on_toggle)
        self.button.connect('button_press_event', self.on_button_press)
        self.glade.signal_autoconnect(self)

        # init hotkey
        dispatcher.add_handler('keybinding_activated', self.on_keybinding_activated)
        dispatcher.add_handler('gconf_timeout_changed', self.on_timeout_changed)
  
        # init idle check
        self.timeout = self.config.get_timeout()
        idle.init()

    def on_today_release_event(self, tree, event):
        pointer = event.window.get_pointer() # x, y, flags
        path = tree.get_path_at_pos(pointer[0], pointer[1]) #column, innerx, innery
        if path[1] == self.edit_column:
            selection = tree.get_selection()
            (model, iter) = selection.get_selected()
            fact_id = model[iter][0]
                
            from hamster.add_custom_fact import CustomFactController
            custom_fact = CustomFactController(None, fact_id)
            custom_fact.show()
            return True
        
        return False
        
    """UI functions"""
    def refresh_hamster(self):
        """refresh hamster every x secs - load today, check last activity etc."""        
        prev_date = self.today
        self.today = datetime.date.today()

        # stop tracking task if computer is idle for 15 minutes
        if self.timeout and self.last_activity and \
           self.last_activity['end_time'] == None and \
           idle.getIdleSec() / 60.0 >= self.timeout:
            storage.touch_fact(self.last_activity)
            
        # if we have date change - let's finish previous task and start a new one
        if prev_date and prev_date != self.today: 
            if self.last_activity and self.last_activity['end_time'] == None:
                storage.touch_fact(self.last_activity)
                storage.add_fact(self.last_activity['name'])
            else:
                self.load_day()
            
        self.update_label()
        return True

    def update_label(self):
        if self.last_activity and self.last_activity['end_time'] == None:
            delta = datetime.datetime.now() - self.last_activity['start_time']
            duration = delta.seconds /  60
            label = "%s %s" % (self.last_activity['name'], format_duration(duration))
            
            self.glade.get_widget('current_activity').set_text(self.last_activity['name'])
            self.glade.get_widget('stop_tracking').set_sensitive(1);
        else:
            label = "%s" % _(u"No activity")
            self.glade.get_widget('stop_tracking').set_sensitive(0);
        self.button.set_text(label)
        
    def load_day(self):
        """sets up today's tree and fills it with records
           returns information about last activity"""
        day = DayStore(self.today);
        self.treeview.set_model(day.fact_store)

        if len(day.facts) == 0:
            self.last_activity = None
            self.glade.get_widget("todays_scroll").hide()
            self.glade.get_widget("no_facts_today").show()
        else:
            self.last_activity = day.facts[len(day.facts) - 1]
            self.glade.get_widget("todays_scroll").show()
            self.glade.get_widget("no_facts_today").hide()
   

    def refresh_menu(self):
        #first populate the autocomplete - contains all entries
        self.activities.clear()
        all_activities = storage.get_activities()
        for activity in all_activities:
            self.activities.append([activity['name']])


        #now populate the menu - contains only categorized entries
        store = self.activity_list.get_model()
        store.clear()

        #populate fresh list from DB
        categorized_activities = storage.get_sorted_activities()

        for activity in categorized_activities:
            item = store.append([activity['name'], activity['id']])

        # finally add TODO tasks from evolution to both lists
        tasks = hamster.eds.get_eds_tasks()
        for activity in tasks:
            self.activities.append([activity['name']])
            store.append([activity['name'], -1])

        return True


    def delete_selected(self):
        selection = self.treeview.get_selection()
        (model, iter) = selection.get_selected()

        next_row = model.iter_next(iter)

        (cur, col) = self.treeview.get_cursor()

        storage.remove_fact(model[iter][0])
        
        self.treeview.set_cursor(cur)


    def __show_toggle(self, event, is_active):
        """main window display and positioning"""
        self.button.set_active(is_active)
        if not is_active:
            self.window.hide()
            return

        self.window.show()

        label_geom = self.button.get_allocation()
        window_geom = self.window.get_allocation()
        
        x, y = self.button.get_pos()

        self.popup_dir = self.applet.get_orient()
        if self.popup_dir in [gnomeapplet.ORIENT_DOWN]:
            y = y + label_geom.height;
        elif self.popup_dir in [gnomeapplet.ORIENT_UP]:
            y = y - window_geom.height;
        
        self.window.move(x, y)

        if self.last_activity and self.last_activity["end_time"] == None:
            self.activity_list.child.set_text(self.last_activity["name"])
            self.activity_list.child.select_region(0, -1)
        else:
            self.activity_list.child.set_text('')

        self.applet.grab_focus()
        self.activity_list.grab_focus()


    """events"""
    def on_button_press(self, widget, event):
        if event.button != 1:
            self.applet.do_button_press_event(self.applet, event)

    def on_toggle(self, widget):
        dispatcher.dispatch('panel_visible', self.button.get_active())

    def on_activity_switched(self, component):
        # do stuff only if user has selected something
        # for other cases activity_edited will be triggered
        if component.get_active_iter():
            component.child.activate() # forward
        return True

    def on_activity_entered(self, component):
        """fires, when user writes activity by hand"""
        activity_name = component.get_text()
        
        if activity_name == "":
            return
        
        storage.add_fact(activity_name)
        dispatcher.dispatch('panel_visible', False)

    """listview events"""
    def on_todays_keys(self, tree, event_key):
        if (event_key.keyval == gtk.keysyms.Delete):
            self.delete_selected()
            return True
        return False
    
    def on_today_row_activated(self, tree, path, column):
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()
        activity_name = model[iter][1]
        if activity_name:
            storage.add_fact(activity_name)
            dispatcher.dispatch('panel_visible', False)        
        
        
    def on_windows_keys(self, tree, event_key):
        if (event_key.keyval == gtk.keysyms.Escape):
            dispatcher.dispatch('panel_visible', False)
            return True
        return False
        
    """button events"""
    def on_stop_tracking(self, button):
        storage.touch_fact(self.last_activity)
        self.last_activity = None
        self.update_label()
        dispatcher.dispatch('panel_visible', False)

    def on_overview(self, menu_item):
        from hamster.stats import StatsViewer
        dispatcher.dispatch('panel_visible', False)
        stats_viewer = StatsViewer()
        stats_viewer.show()

    def on_custom_fact(self, menu_item):
        from hamster.add_custom_fact import CustomFactController
        custom_fact = CustomFactController()
        custom_fact.show()

    def on_about (self, component, verb):
        from hamster.about import show_about
        show_about(self.applet)

    def on_edit_activities(self, menu_item, verb):
        from hamster.activities import ActivitiesEditor

        dispatcher.dispatch('panel_visible', False)
        activities_editor = ActivitiesEditor()
        activities_editor.show()
    
    """signals"""
    def after_activity_update(self, widget, renames):
        self.refresh_menu()
        self.load_day()
        self.update_label()
    
    def after_fact_update(self, event, date):
        if date.date() == datetime.date.today():
            self.load_day()
            self.update_label()

    """global shortcuts"""
    def on_keybinding_activated(self, event, data):
        self.__show_toggle(None, not self.button.get_active())
        
    def on_timeout_changed(self, event, new_timeout):
        self.timeout = new_timeout

