# - coding: utf-8 -

# Copyright (C) 2007-2009 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2007-2009 Patryk Zawadzki <patrys at pld-linux.org>
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

import pygtk
pygtk.require("2.0")
import gtk
gtk.gdk.threads_init()

import gnomeapplet
import gobject
import dbus
import dbus.service
import dbus.mainloop.glib

from hamster import dispatcher, storage, SHARED_DATA_DIR
import hamster.eds
from hamster.Configuration import GconfStore

from hamster import stuff
from hamster.KeyBinder import *
from hamster.hamsterdbus import HAMSTER_URI, HamsterDbusController 

# controllers for other windows
from hamster.edit_activity import CustomFactController
from hamster.stats import StatsViewer
from hamster.about import show_about
from hamster.preferences import PreferencesEditor

import idle

import pango

try:
    import pynotify
    PYNOTIFY = True
except:
    PYNOTIFY = False
    
class Notifier(object):
    def __init__(self, app_name, icon, attach):
        self._icon = icon
        self._attach = attach
        # Title of reminder notification
        self.summary = _("Time Tracker")
      
        if not pynotify.is_initted():
            pynotify.init(app_name)

    def msg(self, body, edit_cb, switch_cb):
        notify = pynotify.Notification(self.summary, body, self._icon, self._attach)

        if "actions" in pynotify.get_server_caps():
            #translators: this is edit activity action in the notifier bubble
            notify.add_action("edit", _("Edit"), edit_cb)
            #translators: this is switch activity action in the notifier bubble
            notify.add_action("switch", _("Switch"), switch_cb)
            
        notify.show()
    
    def msg_low(self, message):
        notify = pynotify.Notification(self.summary, message, self._icon, self._attach)
        notify.set_urgency(pynotify.URGENCY_LOW)
        notify.show()


class PanelButton(gtk.ToggleButton):
    def __init__(self):
        gtk.ToggleButton.__init__(self)
        self.set_relief(gtk.RELIEF_NONE)
        self.set_border_width(0)
        
        self.label = gtk.Label()
        self.label.set_justify(gtk.JUSTIFY_CENTER)

        self.label.connect('style-set', self.on_label_style_set)
        self.connect('size_allocate', self.on_size_allocate)

        self.add(self.label)
        
        self.activity, self.duration = None, None
        self.prev_size = 0

    def set_active(self, is_active):
        self.set_property('active', is_active)

    def set_text(self, activity, duration):
        self.activity = activity
        self.duration = duration
        self.reformat_label()
        
    def reformat_label(self):
        label = self.activity
        if self.duration:
            if self.use_two_line_format():
                label = "%s\n%s" % (self.activity, self.duration)
            else:
                label = "%s %s" % (self.activity, self.duration)
        
        label = stuff.escape_pango(label)
        label = '<span gravity=\"south\">' + label + '</span>'
        self.label.set_markup(label)

    def get_pos(self):
        return gtk.gdk.Window.get_origin(self.label.window)


    def use_two_line_format(self):
        if not self.get_parent():
            return False

        popup_dir = self.get_parent().get_orient()
 
        orient_vertical = popup_dir in [gnomeapplet.ORIENT_LEFT] or \
                          popup_dir in [gnomeapplet.ORIENT_RIGHT]


        context = self.label.get_pango_context()
        metrics = context.get_metrics(self.label.style.font_desc,
                                      pango.Context.get_language(context))
        ascent = pango.FontMetrics.get_ascent(metrics)
        descent = pango.FontMetrics.get_descent(metrics)

        if orient_vertical == False:
            thickness = self.style.ythickness;
        else:
            thickness = self.style.xthickness;

        focus_width = self.style_get_property("focus-line-width")
        focus_pad = self.style_get_property("focus-padding")

        required_size = 2 * ((pango.PIXELS(ascent + descent) ) + 2 * (focus_width + focus_pad + thickness))

        if orient_vertical:
            available_size = self.get_allocation().width
        else:
            available_size = self.get_allocation().height
        
        return required_size <= available_size

    def on_label_style_set(self, widget, something):
        self.reformat_label()


    def on_size_allocate(self, widget, allocation):
        if not self.get_parent():
            return

        self.popup_dir = self.get_parent().get_orient()
        
        orient_vertical = True
        new_size = allocation.width
        if self.popup_dir in [gnomeapplet.ORIENT_LEFT]:
            new_angle = 270
        elif self.popup_dir in [gnomeapplet.ORIENT_RIGHT]:
            new_angle = 90
        else:
            new_angle = 0
            orient_vertical = False
            new_size = allocation.height
        
        if new_angle != self.label.get_angle():
            self.label.set_angle(new_angle)

        if new_size != self.prev_size:
            self.reformat_label()

        self.prev_size = new_size


class HamsterApplet(object):
    def __init__(self, applet):
        self.config = GconfStore.get_instance()
        
        self.applet = applet
        self.applet.set_applet_flags (gnomeapplet.EXPAND_MINOR);
        
        self.notify_interval = None

        self.preferences_editor = None
        self.applet.about = None
        self.open_fact_editors = []

        self.button = PanelButton()
        
        # load window of activity switcher and todays view
        self._gui = stuff.load_ui_file("applet.ui")
        self.window = self._gui.get_object('hamster-window')

        self.set_dropdown()

        # init today's tree
        self.setup_activity_tree()

        # DBus Setup
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            name = dbus.service.BusName(HAMSTER_URI, dbus.SessionBus())
            self.dbusController = HamsterDbusController(bus_name = name)

            # Set up connection to the screensaver
            self.dbusIdleListener = idle.DbusIdleListener()

            # let's also attach our listeners here
            bus = dbus.SessionBus()
            bus.add_signal_receiver(self.on_idle_changed,
                                    dbus_interface="org.gnome.ScreenSaver",
                                    signal_name="SessionIdleChanged")
        except dbus.DBusException, e:
            print "can't init dbus: %s" % e
    
        # Load today's data, activities and set label
        self.last_activity = None

        self.load_day()
        self.update_label()

        # Hamster DBusController current fact initialising
        self.__update_fact()

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
            ("overview", self.show_overview),
            ("preferences", self.show_preferences),
            ])

        self.applet.show_all()
        self.applet.set_background_widget(self.applet)

        self.button.connect('toggled', self.on_toggle)

        self.button.connect('button_press_event', self.on_button_press)
        self._gui.connect_signals(self)

        # init hotkey
        dispatcher.add_handler('keybinding_activated', self.on_keybinding_activated)

        # init idle check
        dispatcher.add_handler('gconf_timeout_enabled_changed', self.on_timeout_enabled_changed)
        self.timeout_enabled = self.config.get_timeout_enabled()

        dispatcher.add_handler('gconf_notify_on_idle_changed', self.on_notify_on_idle_changed)
        self.notify_on_idle = self.config.get_notify_on_idle()
        
        
        # init nagging timeout
        if PYNOTIFY:
            self.notify = Notifier('HamsterApplet', gtk.STOCK_DIALOG_QUESTION, self.button)
            dispatcher.add_handler('gconf_notify_interval_changed', self.on_notify_interval_changed)
            self.on_notify_interval_changed(None, self.config.get_notify_interval())

    def give_more_info(self):
        def on_response(self, widget):
            self.destroy()
        message_dialog = gtk.MessageDialog(buttons = gtk.BUTTONS_OK)
        message_dialog.set_property("title", _("What to type in the activity box?"))
        message_dialog.connect("response", on_response)
        
        more_info = _("""There is simple syntax that enables you to add details to your activities:
        
"@" symbol marks category. Example: "watering flowers@home" will start tracking activity "watering flowers" in category "home".

Comma (",") marks beginning of description. Example: "watering flowers, begonias and forgetmenots" will start tracking activity "watering flowers" and add description "begonias and forgetmenots" to it.

Both can be combined: "watering flowers@home, begonias and forgetmenots" will work just fine!

Now, start tracking!
        """)
        
        message_dialog.set_markup(more_info)
        message_dialog.show()
        
    def on_more_info_button_clicked(self, button):
        self.give_more_info()

    def setup_activity_tree(self):
        self.treeview = self._gui.get_object('today')
        self.treeview.set_tooltip_column(1)
        
        self.treeview.append_column(gtk.TreeViewColumn("Time", gtk.CellRendererText(), text=2))

        nameColumn = stuff.ActivityColumn(name=1, description=5, category=6)
        self.treeview.append_column(nameColumn)

        
        duration_cell = gtk.CellRendererText()
        duration_cell.set_property("xalign", 1)
        timeColumn = gtk.TreeViewColumn(_("Duration"), duration_cell, text=3)
        
        self.treeview.append_column(timeColumn)

        edit_cell = gtk.CellRendererPixbuf()
        edit_cell.set_property("stock_id", "gtk-edit")
        edit_cell.set_property("mode", gtk.CELL_RENDERER_MODE_ACTIVATABLE)
        self.edit_column = gtk.TreeViewColumn("", edit_cell)
        self.treeview.append_column(self.edit_column)


    def on_idle_changed(self, state):
        print "Idle state changed. Idle: ", state
        # refresh when we are out of idle
        # (like, instantly after computer has been turned on!
        if state == 0:
            self.refresh_hamster() 
        
    def set_dropdown(self):
        # set up drop down menu
        self.activity_list = self._gui.get_object('activity-list')
        self.activity_list.child.connect('activate', self.on_activity_entered)
        self.activity_list.child.connect('key-press-event', self.on_activity_list_key_pressed)

        self.activity_list.set_model(gtk.ListStore(gobject.TYPE_STRING,
                                                   gobject.TYPE_STRING,
                                                   gobject.TYPE_STRING))

        self.activity_list.clear()
        activity_cell = gtk.CellRendererText()
        self.activity_list.pack_start(activity_cell, True)
        self.activity_list.add_attribute(activity_cell, 'text', 0)

        category_cell = stuff.CategoryCell()  
        self.activity_list.pack_start(category_cell, False)
        self.activity_list.add_attribute(category_cell, 'text', 1)
        
        self.activity_list.set_property("text-column", 2)


        # set up autocompletition
        self.activities = gtk.ListStore(gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING)
        completion = gtk.EntryCompletion()
        completion.set_model(self.activities)

        activity_cell = gtk.CellRendererText()
        completion.pack_start(activity_cell, True)
        completion.add_attribute(activity_cell, 'text', 0)
        completion.set_property("text-column", 2)

        category_cell = stuff.CategoryCell()  
        completion.pack_start(category_cell, False)
        completion.add_attribute(category_cell, 'text', 1)


        def match_func(completion, key, iter):
            model = completion.get_model()
            text = model.get_value(iter, 2)
            if text and text.startswith(key):
                return True
            return False

        completion.set_match_func(match_func)
        completion.set_minimum_key_length(1)
        completion.set_inline_completion(True)

        self.activity_list.child.set_completion(completion)
        

    def on_today_release_event(self, tree, event):
        pointer = event.window.get_pointer() # x, y, flags
        path = tree.get_path_at_pos(pointer[0], pointer[1]) #column, innerx, innery
        
        if path and path[1] == self.edit_column:
            self._open_edit_activity()
            return True
        
        return False
        
    """UI functions"""
    def refresh_hamster(self):
        """refresh hamster every x secs - load today, check last activity etc."""        
        # stop tracking task if computer is idle for X minutes
        if self.timeout_enabled and self.last_activity and \
           self.last_activity['end_time'] == None:
            if self.dbusIdleListener.is_idle:
                # Only subtract idle time from the running task when
                # idleness is due to time out, not a screen lock.
                if self.dbusIdleListener.is_screen_locked:
                    idle_minutes = 0
                else:
                    idle_minutes = idle.getIdleSec() / 60.0
                current_time = datetime.datetime.now()
                idle_from = current_time - datetime.timedelta(minutes = idle_minutes)
                storage.touch_fact(self.last_activity, end_time = idle_from)
            

            # if we have date change - let's finish previous task and start a new one
            if self.button.get_active(): # otherwise if we the day view is visible - update day's durations
                self.load_day()
                    
        self.update_label()
        self.check_user()
        return True

    def update_label(self):
        if self.last_activity and self.last_activity['end_time'] == None:
            delta = datetime.datetime.now() - self.last_activity['start_time']
            duration = delta.seconds /  60
            label = "%s %s" % (self.last_activity['name'],
                                                stuff.format_duration(duration, False))
            self.button.set_text(self.last_activity['name'],
                                                stuff.format_duration(duration, False))
            
            self._gui.get_object('stop_tracking').set_sensitive(1);
        else:
            label = "%s" % _(u"No activity")
            self.button.set_text(label, None)
            self._gui.get_object('stop_tracking').set_sensitive(0);
        
        
        # Hamster DBusController current activity updating
        self.dbusController.update_activity(label)

    def check_user(self):
        if not self.notify_interval: #no interval means "never"
            return
        
        now = datetime.datetime.now()
        if self.last_activity:
            delta = now - self.last_activity['start_time']
            duration = delta.seconds /  60

            if duration and duration % self.notify_interval == 0:
                # activity reminder
                msg = _(u"Working on <b>%s</b>") % self.last_activity['name']
                self.notify.msg(msg, self.edit_cb, self.switch_cb)
        elif self.notify_on_idle:
            #if we have no last activity, let's just calculate duration from 00:00
            if (now.minute + now.hour *60) % self.notify_interval == 0:
                self.notify.msg_low(_(u"No activity"))

    def edit_cb(self, n, action):
        custom_fact = CustomFactController(self, None, self.last_activity['id'])
        custom_fact.show()

    def switch_cb(self, n, action):
        self.__show_toggle(None, not self.button.get_active())	


    def load_day(self):
        """sets up today's tree and fills it with records
           returns information about last activity"""
        today = datetime.date.today()

        self.last_activity = None
        last_activity = storage.get_last_activity()
        if last_activity and last_activity["start_time"].date() >= \
                                            today - datetime.timedelta(days=1):
            self.last_activity = last_activity


        # ID, Time, Name, Duration, Date, Description, Category
        fact_store = gtk.ListStore(int, str, str, str, str, str, str)
        facts = storage.get_facts(today)
        
        totals = {}
        
        for fact in facts:
            duration = None
            
            if fact["delta"]:
                duration = 24 * fact["delta"].days + fact["delta"].seconds / 60
            
            fact_category = fact['category']
            
            if fact_category not in totals:
                totals[fact_category] = 0

            if duration:
                totals[fact_category] += duration

            current_duration = stuff.format_duration(duration)
            
            fact_store.append([fact['id'],
                                    stuff.escape_pango(fact['name']), 
                                    fact["start_time"].strftime("%H:%M"), 
                                    "%s" % current_duration,
                                    fact["start_time"].strftime("%H:%M"),
                                    stuff.escape_pango(fact["description"]),
                                    stuff.escape_pango(fact["category"])])



        self.treeview.set_model(fact_store)

        
        if len(facts) == 0:
            self._gui.get_object("todays_scroll").hide()
            self._gui.get_object("fact_totals").set_text(_("No records today"))
        else:
            self._gui.get_object("todays_scroll").show()
            
            total_strings = []
            for total in totals:
                # listing of today's categories and time spent in them
                total_strings.append(_("%(category)s: %(duration)s") % \
                        ({'category': total,
                          'duration': _("%.1fh") % (totals[total] / 60.0)}))

            total_string = ", ".join(total_strings)
            self._gui.get_object("fact_totals").set_text(total_string)
   

    def refresh_menu(self):
        #first populate the autocomplete - contains all entries in lowercase
        self.activities.clear()
        all_activities = storage.get_autocomplete_activities()
        for activity in all_activities:
            activity_category = activity['name']
            if activity['category']:
                activity_category += "@%s" % activity['category']
                
            self.activities.append([activity['name'],
                                    activity['category'],
                                    activity_category])


        #now populate the menu - contains only categorized entries
        store = self.activity_list.get_model()
        store.clear()

        #populate fresh list from DB
        categorized_activities = storage.get_sorted_activities()

        for activity in categorized_activities:
            activity_category = activity['name']
            if activity['category']:
                activity_category += "@%s" % activity['category']

            item = store.append([activity['name'],
                                 activity['category'],
                                 activity_category])

        # finally add TODO tasks from evolution to both lists
        tasks = hamster.eds.get_eds_tasks()
        for activity in tasks:
            activity_category = "%s@%s" % (activity['name'], activity['category'])
            self.activities.append([activity['name'],activity['category'],activity_category])
            store.append([activity['name'], activity['category'], activity_category])

        return True


    def delete_selected(self):
        selection = self.treeview.get_selection()
        (model, iter) = selection.get_selected()

        next_row = model.iter_next(iter)

        (cur, col) = self.treeview.get_cursor()

        storage.remove_fact(model[iter][0])
        
        self.treeview.set_cursor(cur)


    def __update_fact(self):
        """dbus controller current fact updating"""
        if self.last_activity and self.last_activity['end_time'] == None:
            self.dbusController.update_fact(self.last_activity["name"])
        else:
            self.dbusController.update_fact(_(u'No activity'))


    def __show_toggle(self, event, is_active):
        """main window display and positioning"""
        self.button.set_active(is_active)
        if not is_active:
            self.window.hide()
            return

        self.load_day() # reload day each time before showing to avoid outdated last activity
        self.update_label() #update also label, otherwise we can get 1 minute difference in durations (due to timers refreshed once a minute)

        label_geom = self.button.get_allocation()
        window_geom = self.window.get_allocation()
        
        x, y = self.button.get_pos()

        self.popup_dir = self.applet.get_orient()
        if self.popup_dir == gnomeapplet.ORIENT_DOWN:
            y = y + label_geom.height
        elif self.popup_dir == gnomeapplet.ORIENT_UP:
            y = y - window_geom.height
        elif self.popup_dir == gnomeapplet.ORIENT_RIGHT:
            x = x + label_geom.width
        elif self.popup_dir == gnomeapplet.ORIENT_LEFT:
            x = x - window_geom.width

        self.window.move(x, y)


        if self.last_activity and self.last_activity["end_time"] == None:
            label = self.last_activity['name']
            if self.last_activity['category'] != _("Unsorted"):
                label += "@%s" %  self.last_activity['category']
            self.activity_list.child.set_text(label)

            self.activity_list.child.select_region(0, -1)
            self._gui.get_object("more_info_label").hide()
        else:
            self.activity_list.child.set_text('')
            self._gui.get_object("more_info_label").show()

        # doing unstick / stick here, because sometimes while switching
        # between workplaces window still manages to dissappear
        self.window.unstick()
        self.window.stick() #show on all desktops

        gobject.idle_add(self._delayed_display)  
        
    def _delayed_display(self):
        """show window only when gtk has become idle. otherwise we get
        mixed results. TODO - this looks like a hack though"""
        self.window.present()
        self.activity_list.grab_focus()
        

    """events"""
    def on_button_press(self, widget, event):
        if event.button != 1:
            widget.stop_emission('button_press_event')
        return False

    def on_toggle(self, widget):
        dispatcher.dispatch('panel_visible', self.button.get_active())

    def on_activity_list_key_pressed(self, entry, event):
        #treating tab as keydown to be able to cycle through available values
        if event.keyval == gtk.keysyms.Tab:
            event.keyval = gtk.keysyms.Down
        return False
        
    def on_activity_switched(self, component):
        # do stuff only if user has selected something
        # for other cases activity_edited will be triggered
        if component.get_active_iter():
            component.child.activate() # forward
        return True

    def on_activity_entered(self, component):
        """fires, when user writes activity by hand"""
        activity_name = component.get_text().decode('utf8', 'replace')
        
        if activity_name == "":
            return
        
        storage.add_fact(activity_name)
        dispatcher.dispatch('panel_visible', False)

    """listview events"""
    def on_todays_keys(self, tree, event):
        if (event.keyval == gtk.keysyms.Delete):
            self.delete_selected()
            return True
        elif (event.keyval == gtk.keysyms.e  \
              and event.state & gtk.gdk.CONTROL_MASK):
            self._open_edit_activity()
            return True
            
        return False
    
    def _open_edit_activity(self):
        """opens activity editor for selected row"""
        selection = self.treeview.get_selection()
        (model, iter) = selection.get_selected()
        fact_id = model[iter][0]
            
        custom_fact = CustomFactController(self, None, fact_id)
        custom_fact.show()        
    
    def on_today_row_activated(self, tree, path, column):
        if column == self.edit_column:
            self._open_edit_activity()
        else:
            selection = tree.get_selection()
            (model, iter) = selection.get_selected()
            activity_name = model[iter][1].decode('utf8', 'replace')
            if activity_name:
                description = model[iter][5]
                if description:
                    description = description.decode('utf8', 'replace')
                    activity_name = "%s, %s" % (activity_name, description)
                    
                storage.add_fact(activity_name)
                dispatcher.dispatch('panel_visible', False)
        
        
    def on_windows_keys(self, tree, event_key):
        if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w 
              and event_key.state & gtk.gdk.CONTROL_MASK)):
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
        dispatcher.dispatch('panel_visible', False)
        stats_viewer = StatsViewer(self)
        stats_viewer.show()

    def show_overview(self, menu_item, verb):
        return self.on_overview(menu_item)

    def on_custom_fact(self, menu_item):
        custom_fact = CustomFactController(self)
        custom_fact.show()

    def on_about (self, component, verb):
        if self.applet.about:
            self.applet.about.present()
        else:
            show_about(self.applet)

    def show_preferences(self, menu_item, verb):
        dispatcher.dispatch('panel_visible', False)
        
        if self.preferences_editor and self.preferences_editor.window:
            self.preferences_editor.window.present()
        else:
            self.preferences_editor = PreferencesEditor(self)
            self.preferences_editor.show()
    
    """signals"""
    def after_activity_update(self, widget, renames):
        self.refresh_menu()
        self.load_day()
        self.update_label()
    
    def after_fact_update(self, event, date):
        self.load_day()
        self.update_label()
    
        self.__update_fact()

    """global shortcuts"""
    def on_keybinding_activated(self, event, data):
        self.__show_toggle(None, not self.button.get_active())
        
    def on_timeout_enabled_changed(self, event, enabled):
        # if enabled, set to value, otherwise set to zero, which means disable
        self.timeout_enabled = enabled

    def on_notify_on_idle_changed(self, event, enabled):
        # if enabled, set to value, otherwise set to zero, which means disable
        self.notify_on_idle = enabled

    def on_notify_interval_changed(self, event, new_interval):
        if PYNOTIFY and 0 < new_interval < 121:
            self.notify_interval = new_interval
        else:
            self.notify_interval = None
