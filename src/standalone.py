#!/usr/bin/env python
# - coding: utf-8 -

# Copyright (C) 2009, 2010 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2009 Patryk Zawadzki <patrys at pld-linux.org>

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
import datetime as dt

import gtk

import gobject
import dbus, dbus.service, dbus.mainloop.glib

from hamster import eds
from hamster.configuration import conf, runtime, dialogs

from hamster import stuff
from hamster.hamsterdbus import HAMSTER_URI, HamsterDbusController

# controllers for other windows
from hamster import widgets
from hamster import idle

try:
    import wnck
except:
    logging.warning("Could not import wnck - workspace tracking will be disabled")
    wnck = None

try:
    import pynotify
    pynotify.init('Hamster Applet')
except:
    logging.warning("Could not import pynotify - notifications will be disabled")
    pynotify = None

class ProjectHamster(object):
    def __init__(self):
        # load window of activity switcher and todays view
        self._gui = stuff.load_ui_file("hamster.ui")
        self.window = self._gui.get_object('hamster-window')
        self.window.connect("delete_event", self.close_window)

        self.new_name = widgets.ActivityEntry()
        self.new_name.connect("value-entered", self.on_switch_activity_clicked)
        widgets.add_hint(self.new_name, _("Activity"))
        self.get_widget("new_name_box").add(self.new_name)
        self.new_name.connect("changed", self.on_activity_text_changed)

        self.new_tags = widgets.TagsEntry()
        self.new_tags.connect("tags_selected", self.on_switch_activity_clicked)
        widgets.add_hint(self.new_tags, _("Tags"))
        self.get_widget("new_tags_box").add(self.new_tags)

        self.tag_box = widgets.TagBox(interactive = False)
        self.get_widget("tag_box").add(self.tag_box)

        self.treeview = widgets.FactTree()
        self.treeview.connect("key-press-event", self.on_todays_keys)
        self.treeview.connect("edit-clicked", self._open_edit_activity)
        self.treeview.connect("row-activated", self.on_today_row_activated)

        self.get_widget("today_box").add(self.treeview)

        # DBus Setup
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            name = dbus.service.BusName(HAMSTER_URI, dbus.SessionBus())
            self.dbusController = HamsterDbusController(bus_name = name)

            # Set up connection to the screensaver
            self.dbusIdleListener = idle.DbusIdleListener(runtime.dispatcher)
            runtime.dispatcher.add_handler('active_changed', self.on_idle_changed)

        except dbus.DBusException, e:
            logging.error("Can't init dbus: %s" % e)

        # configuration
        self.timeout_enabled = conf.get("enable_timeout")
        self.notify_on_idle = conf.get("notify_on_idle")
        self.notify_interval = conf.get("notify_interval")
        self.workspace_tracking = conf.get("workspace_tracking")

        runtime.dispatcher.add_handler('conf_changed', self.on_conf_changed)

        # Load today's data, activities and set label
        self.last_activity = None
        self.load_day()

        # Hamster DBusController current fact initialising
        self.__update_fact()

        # refresh hamster every 60 seconds to update duration
        gobject.timeout_add_seconds(60, self.refresh_hamster)

        runtime.dispatcher.add_handler('activity_updated', self.after_activity_update)
        runtime.dispatcher.add_handler('day_updated', self.after_fact_update)

        self.screen = None
        if self.workspace_tracking:
            self.init_workspace_tracking()

        self.notification = None
        if pynotify:
            self.notification = pynotify.Notification("Oh hi",
                                                      "Greetings from hamster!")
            self.notification.set_urgency(pynotify.URGENCY_LOW) # lower than grass

        self._gui.connect_signals(self)

        self.prev_size = None

        if conf.get("standalone_window_maximized"):
            self.window.maximize()
        else:
            window_box = conf.get("standalone_window_box")
            if window_box:
                x,y,w,h = (int(i) for i in window_box)
                self.window.move(x, y)
                self.window.move(x, y)
                self.window.resize(w, h)
            else:
                self.window.set_position(gtk.WIN_POS_CENTER)

        self.window.show_all()


    def init_workspace_tracking(self):
        if not wnck: # can't track if we don't have the trackable
            return

        self.screen = wnck.screen_get_default()
        self.screen.workspace_handler = self.screen.connect("active-workspace-changed", self.on_workspace_changed)
        self.workspace_activities = {}

    """UI functions"""
    def refresh_hamster(self):
        """refresh hamster every x secs - load today, check last activity etc."""
        try:
            self.check_user()
        finally:  # we want to go on no matter what, so in case of any error we find out about it sooner
            return True

    def check_user(self):
        if not self.notification:
            return

        if self.notify_interval <= 0 or self.notify_interval >= 121:
            return

        now = dt.datetime.now()
        message = None
        if self.last_activity:
            delta = now - self.last_activity['start_time']
            duration = delta.seconds /  60

            if duration and duration % self.notify_interval == 0:
                message = _(u"Working on <b>%s</b>") % self.last_activity['name']

        elif self.notify_on_idle:
            #if we have no last activity, let's just calculate duration from 00:00
            if (now.minute + now.hour *60) % self.notify_interval == 0:
                message = _(u"No activity")


        if message:
            self.notification.update(_("Time Tracker"), message, "hamster-applet")
            self.notification.show()


    def edit_cb(self, n, action):
        dialogs.edit.show(self.applet, activity_id = self.last_activity['id'])


    def load_day(self):
        """sets up today's tree and fills it with records
           returns information about last activity"""

        facts = runtime.storage.get_todays_facts()

        self.treeview.detach_model()
        self.treeview.clear()

        if facts and facts[-1]["end_time"] == None:
            self.last_activity = facts[-1]
        else:
            self.last_activity = None

        by_category = {}
        for fact in facts:
            duration = 24 * 60 * fact["delta"].days + fact["delta"].seconds / 60
            by_category[fact['category']] = \
                          by_category.setdefault(fact['category'], 0) + duration
            self.treeview.add_fact(fact)

        self.treeview.attach_model()

        if not facts:
            self._gui.get_object("today_box").hide()
            #self._gui.get_object("fact_totals").set_text(_("No records today"))
        else:
            self._gui.get_object("today_box").show()

        self.set_last_activity()

    def set_last_activity(self):
        activity = self.last_activity
        #sets all the labels and everything as necessary
        self.get_widget("stop_tracking").set_sensitive(activity != None)


        if activity:
            self.get_widget("switch_activity").show()
            self.get_widget("start_tracking").hide()

            delta = dt.datetime.now() - activity['start_time']
            duration = delta.seconds /  60

            self._gui.get_object("more_info_button").hide()
            self.get_widget("last_activity_duration").show()
            self.get_widget("last_activity_description").show()
            self.get_widget("last_activity_category").show()

            self.get_widget("last_activity_duration").set_text(stuff.format_duration(duration) or _("Just started"))

            self.get_widget("last_activity_name").set_text(activity['name'])
            if activity['category'] != _("Unsorted"):
                self.get_widget("last_activity_category") \
                    .set_text(" - %s" % activity['category'])

            self.get_widget("last_activity_description").set_text(activity['description'] or "")

            self.tag_box.draw(activity["tags"])
        else:
            self.get_widget("switch_activity").hide()
            self.get_widget("start_tracking").show()

            self.get_widget("last_activity_name").set_text(_("No activity"))

            self.get_widget("last_activity_duration").hide()
            self._gui.get_object("more_info_button").show()

            self.get_widget("last_activity_category").hide()
            self.tag_box.draw([])
            self.get_widget("last_activity_description").hide()


    def delete_selected(self):
        fact = self.treeview.get_selected_fact()
        runtime.storage.remove_fact(fact["id"])

    def __update_fact(self):
        """dbus controller current fact updating"""
        last_activity_id = 0

        if not self.last_activity:
            self.dbusController.TrackingStopped()
        else:
            last_activity_id = self.last_activity['id']

        self.dbusController.FactUpdated(last_activity_id)

    def _delayed_display(self):
        """show window only when gtk has become idle. otherwise we get
        mixed results. TODO - this looks like a hack though"""
        self.window.present()
        self.new_name.grab_focus()


    """events"""
    def on_todays_keys(self, tree, event):
        if (event.keyval == gtk.keysyms.Delete):
            self.delete_selected()
            return True

        return False

    def _open_edit_activity(self, row, fact):
        """opens activity editor for selected row"""
        dialogs.edit.show(self.applet, fact_id = fact["id"])

    def on_today_row_activated(self, tree, path, column):
        fact = tree.get_selected_fact()

        if fact:
            runtime.storage.add_fact(fact["name"],
                                     ", ".join(fact["tags"]),
                                     category_name = fact["category"],
                                     description = fact["description"])
            runtime.dispatcher.dispatch('panel_visible', False)


    def on_windows_keys(self, tree, event_key):
        if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w
              and event_key.state & gtk.gdk.CONTROL_MASK)):
            if self.new_name.popup.get_property("visible") == False \
               and self.new_tags.popup.get_property("visible") == False:
                runtime.dispatcher.dispatch('panel_visible', False)
                return True
        return False

    """button events"""
    def on_overview(self, menu_item):
        runtime.dispatcher.dispatch('panel_visible', False)
        dialogs.overview.show(self.applet)

    def show_overview(self, menu_item, verb):
        return self.on_overview(menu_item)

    def on_custom_fact(self, menu_item):
        dialogs.edit.show(self.applet)

    def on_about (self, component, verb):
        dialogs.about.show()

    def show_preferences(self, menu_item, verb):
        runtime.dispatcher.dispatch('panel_visible', False)
        dialogs.prefs.show(self.applet)


    """signals"""
    def after_activity_update(self, widget, renames):
        self.new_name.refresh_activities()
        self.load_day()

    def after_fact_update(self, event, date):
        self.load_day()
        self.__update_fact()

    def on_idle_changed(self, event, state):
        # state values: 0 = active, 1 = idle

        # refresh when we are out of idle
        # for example, instantly after coming back from suspend
        if state == 0:
            self.refresh_hamster()
        elif self.timeout_enabled and self.last_activity and \
             self.last_activity['end_time'] is None:

            runtime.storage.touch_fact(self.last_activity,
                                       end_time = self.dbusIdleListener.getIdleFrom())

    def on_workspace_changed(self, screen, previous_workspace):
        if not previous_workspace:
            # wnck has a slight hiccup on init and after that calls
            # workspace changed event with blank previous state that should be
            # ignored
            return

        if not self.workspace_tracking:
            return # default to not doing anything

        current_workspace = screen.get_active_workspace()

        # rely on workspace numbers as names change
        prev = previous_workspace.get_number()
        new = current_workspace.get_number()

        # on switch, update our mapping between spaces and activities
        self.workspace_activities[prev] = self.last_activity


        activity = None
        if "name" in self.workspace_tracking:
            # first try to look up activity by desktop name
            mapping = conf.get("workspace_mapping")

            parsed_activity = None
            if new < len(mapping):
                parsed_activity = stuff.parse_activity_input(mapping[new])

            if parsed_activity:
                category_id = None
                if parsed_activity.category_name:
                    category_id = runtime.storage.get_category_by_name(parsed_activity.category_name)

                activity = runtime.storage.get_activity_by_name(parsed_activity.activity_name,
                                                                category_id,
                                                                ressurect = False)
                if activity:
                    # we need dict below
                    activity = dict(name = activity['name'],
                                    category = activity['category'],
                                    description = parsed_activity.description,
                                    tags = parsed_activity.tags)


        if not activity and "memory" in self.workspace_tracking:
            # now see if maybe we have any memory of the new workspace
            # (as in - user was here and tracking Y)
            # if the new workspace is in our dict, switch to the specified activity
            if new in self.workspace_activities and self.workspace_activities[new]:
                activity = self.workspace_activities[new]

        if not activity:
            return

        # check if maybe there is no need to switch, as field match:
        if self.last_activity and \
           self.last_activity['name'].lower() == activity['name'].lower() and \
           (self.last_activity['category'] or "").lower() == (activity['category'] or "").lower() and \
           ", ".join(self.last_activity['tags']).lower() == ", ".join(activity['tags']).lower():
            return

        # ok, switch
        runtime.storage.add_fact(activity['name'],
                                 ", ".join(activity['tags']),
                                 category_name = activity['category'],
                                 description = activity['description'])

        if self.notification:
            self.notification.update(_("Changed activity"),
                                     _("Switched to '%s'") % activity['name'],
                                     "hamster-applet")
            self.notification.show()

    """global shortcuts"""
    def on_conf_changed(self, event, data):
        key, value = data

        if key == "enable_timeout":
            self.timeout_enabled = value
        elif key == "notify_on_idle":
            self.notify_on_idle = value
        elif key == "notify_interval":
            self.notify_interval = value
        elif key == "day_start_minutes":
            self.load_day()

        elif key == "workspace_tracking":
            self.workspace_tracking = value
            if self.workspace_tracking and not self.screen:
                self.init_workspace_tracking()
            elif not self.workspace_tracking:
                if self.screen:
                    self.screen.disconnect(self.screen.workspace_handler)
                    self.screen = None


    def on_activity_text_changed(self, widget):
        self.get_widget("switch_activity").set_sensitive(widget.get_text() != "")

    def on_switch_activity_clicked(self, widget):
        if not self.new_name.get_text():
            return False

        runtime.storage.add_fact(self.new_name.get_text().decode("utf8", "replace"),
                                 self.new_tags.get_text().decode("utf8", "replace"))
        self.new_name.set_text("")
        self.new_tags.set_text("")
        runtime.dispatcher.dispatch('panel_visible', False)

    def on_stop_tracking_clicked(self, widget):
        runtime.storage.touch_fact(self.last_activity)
        self.last_activity = None
        runtime.dispatcher.dispatch('panel_visible', False)

    def on_window_configure_event(self, window, event):
        self.treeview.fix_row_heights()

    def show(self):
        self.window.show_all()

    def get_widget(self, name):
        return self._gui.get_object(name)

    def on_more_info_button_clicked(self, *args):
        gtk.show_uri(gtk.gdk.Screen(), "ghelp:hamster-applet", 0L)
        return False

    def close_window(self, *args):
        # properly saving window state and position
        maximized = self.window.get_window().get_state() & gtk.gdk.WINDOW_STATE_MAXIMIZED
        conf.set("standalone_window_maximized", maximized)

        # make sure to remember dimensions only when in normal state
        if maximized == False and not self.window.get_window().get_state() & gtk.gdk.WINDOW_STATE_ICONIFIED:
            x, y = self.window.get_position()
            w, h = self.window.get_size()
            conf.set("standalone_window_box", [x, y, w, h])

        gtk.main_quit()

if __name__ == "__main__":
    gtk.gdk.threads_init()
    app = ProjectHamster()
    gtk.main()
