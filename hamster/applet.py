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

import logging
import datetime as dt

import pygtk
pygtk.require("2.0")
import gtk
gtk.gdk.threads_init()

import gnomeapplet
import gobject
import dbus, dbus.service, dbus.mainloop.glib

import eds
from configuration import conf, runtime, dialogs

import stuff
from KeyBinder import *
from hamsterdbus import HAMSTER_URI, HamsterDbusController

# controllers for other windows
import widgets
import idle

import pango

try:
    import pynotify
    PYNOTIFY = True
except:
    PYNOTIFY = False

class Notifier(object):
    def __init__(self, attach):
        self._icon = gtk.STOCK_DIALOG_QUESTION
        self._attach = attach
        # Title of reminder notification
        self.summary = _("Time Tracker")

        if not pynotify.is_initted():
            pynotify.init('Hamster Applet')

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
        self.connect('button_press_event', self.on_button_press)

        self.add(self.label)

        self.activity, self.duration = None, None
        self.prev_size = 0


        # remove padding, so we fit on small panels (adapted from clock applet)
        gtk.rc_parse_string ("""style "hamster-applet-button-style" {
                GtkWidget::focus-line-width=0
                GtkWidget::focus-padding=0
            }

            widget "*.hamster-applet-button" style "hamster-applet-button-style"
        """);
        gtk.Widget.set_name (self, "hamster-applet-button");


    def set_active(self, is_active):
        self.set_property('active', is_active)

    def set_text(self, activity, duration):
        activity = stuff.escape_pango(activity)
        if len(activity) > 25:  #ellipsize at some random length
            activity = "%s%s" % (activity[:25], "&#8230;")

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

        label = '<span gravity="south">%s</span>' % label
        self.label.set_markup("") #clear - seems to fix the warning
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

    def on_button_press(self, widget, event):
        # this allows dragging applet around panel and friends
        if event.button != 1:
            widget.stop_emission('button_press_event')
        return False


class HamsterApplet(object):
    def __init__(self, applet):
        self.applet = applet

        self.notify_interval = None
        self.preferences_editor = None
        self.applet.about = None
        self.open_fact_editors = []

        self.button = PanelButton()
        self.button.connect('toggled', self.on_toggle)
        self.applet.add(self.button)

        self.applet.setup_menu_from_file (runtime.data_dir,
                                          "Hamster_Applet.xml",
                                          None,
                                          [("about", self.on_about),
                                          ("overview", self.show_overview),
                                          ("preferences", self.show_preferences),
                                          ])

        # load window of activity switcher and todays view
        self._gui = stuff.load_ui_file("applet.ui")
        self.window = self._gui.get_object('hamster-window')

        self.new_name = widgets.ActivityEntry()
        self.new_name.connect("value-entered", self.on_switch_activity_clicked)
        widgets.add_hint(self.new_name, _("Time and Name"))
        self.get_widget("new_name_box").add(self.new_name)
        self.new_name.connect("changed", self.on_activity_text_changed)

        self.new_tags = widgets.TagsEntry()
        widgets.add_hint(self.new_tags, _("Tags or Description"))
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

        self.day_start = conf.get("day_start_minutes")
        self.day_start = dt.time(self.day_start / 60, self.day_start % 60) # it comes in as minutes

        # Load today's data, activities and set label
        self.last_activity = None
        self.load_day()
        self.update_label()

        # Hamster DBusController current fact initialising
        self.__update_fact()

        # refresh hamster every 60 seconds to update duration
        gobject.timeout_add_seconds(60, self.refresh_hamster)


        runtime.dispatcher.add_handler('panel_visible', self.__show_toggle)
        runtime.dispatcher.add_handler('activity_updated', self.after_activity_update)
        runtime.dispatcher.add_handler('day_updated', self.after_fact_update)


        self._gui.connect_signals(self)

        # init hotkey
        runtime.dispatcher.add_handler('keybinding_activated', self.on_keybinding_activated)

        # init idle check
        self.timeout_enabled = conf.get("enable_timeout")
        self.notify_on_idle = conf.get("notify_on_idle")


        # init nagging timeout
        if PYNOTIFY:
            self.notify = Notifier(self.button)
            self.on_conf_changed(None, ("notify_interval", conf.get("notify_interval")))


    """UI functions"""
    def refresh_hamster(self):
        """refresh hamster every x secs - load today, check last activity etc."""

        #if we the day view is visible - update day's durations
        if self.button.get_active():
            self.load_day()

        self.update_label()
        self.check_user()
        return True

    def update_label(self):
        if self.last_activity and self.last_activity['end_time'] is None:
            delta = dt.datetime.now() - self.last_activity['start_time']
            duration = delta.seconds /  60
            label = "%s %s" % (self.last_activity['name'],
                               stuff.format_duration(duration, False))
            self.button.set_text(self.last_activity['name'],
                                 stuff.format_duration(duration, False))
        else:
            label = "%s" % _(u"No activity")
            self.button.set_text(label, None)


    def check_user(self):
        if not self.notify_interval: #no interval means "never"
            return

        now = dt.datetime.now()
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
        dialogs.edit.show(self.applet, activity_id = self.last_activity['id'])

    def switch_cb(self, n, action):
        self.__show_toggle(None, not self.button.get_active())


    def load_day(self):
        """sets up today's tree and fills it with records
           returns information about last activity"""

        today = (dt.datetime.now() - dt.timedelta(hours = self.day_start.hour,
                                                  minutes = self.day_start.minute)).date()

        self.treeview.clear()

        facts = runtime.storage.get_facts(today)
        if facts and facts[-1]["end_time"] == None:
            self.last_activity = facts[-1]
        else:
            self.last_activity = None

        if len(facts) > 10:
            self._gui.get_object("today_box").set_size_request(-1, 250)
            self._gui.get_object("today_box").set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        else:
            self._gui.get_object("today_box").set_size_request(-1, -1)
            self._gui.get_object("today_box").set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_NEVER)

        by_category = {}
        for fact in facts:
            duration = 24 * 60 * fact["delta"].days + fact["delta"].seconds / 60
            by_category[fact['category']] = \
                          by_category.setdefault(fact['category'], 0) + duration
            self.treeview.add_fact(fact)


        if not facts:
            self._gui.get_object("today_box").hide()
            self._gui.get_object("fact_totals").set_text(_("No records today"))
        else:
            self._gui.get_object("today_box").show()

            total_strings = []
            for category in by_category:
                # listing of today's categories and time spent in them
                duration = "%.1f" % (by_category[category] / 60.0)
                total_strings.append(_("%(category)s: %(duration)s") % \
                        ({'category': category,
                          #duration in main drop-down per category in hours
                          'duration': _("%sh") % duration
                          }))

            total_string = ", ".join(total_strings)
            self._gui.get_object("fact_totals").set_text(total_string)

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
            self.get_widget("last_activity_duration").set_text("")
            self.get_widget("last_activity_category").set_text("")
            self.tag_box.draw([])
            self.get_widget("last_activity_description").set_text("")

    def delete_selected(self):
        selection = self.treeview.get_selection()
        (model, iter) = selection.get_selected()

        next_row = model.iter_next(iter)
        (cur, col) = self.treeview.get_cursor()
        runtime.storage.remove_fact(model[iter][0])

        if next_row:
            self.treeview.set_cursor(cur)


    def __update_fact(self):
        """dbus controller current fact updating"""
        last_activity_id = 0

        if not self.last_activity:
            self.dbusController.TrackingStopped()
        else:
            last_activity_id = self.last_activity['id']

        self.dbusController.FactUpdated(last_activity_id)

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



        # doing unstick / stick here, because sometimes while switching
        # between workplaces window still manages to dissappear
        self.window.unstick()
        self.window.stick() #show on all desktops

        self.new_name.set_text("");
        self.new_tags.set_text("");
        gobject.idle_add(self._delayed_display)

    def _delayed_display(self):
        """show window only when gtk has become idle. otherwise we get
        mixed results. TODO - this looks like a hack though"""
        self.window.present()
        self.new_name.grab_focus()


    """events"""
    def on_toggle(self, widget):
        self.__show_toggle(None, self.button.get_active())


    def on_todays_keys(self, tree, event):
        if (event.keyval == gtk.keysyms.Delete):
            self.delete_selected()
            return True

        return False

    def _open_edit_activity(self, row, fact):
        """opens activity editor for selected row"""
        dialogs.edit.show(self.applet, fact_id = fact["id"])

    def on_today_row_activated(self, tree, path, column):
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()

        fact = model[iter][6]
        if fact:
            activity = fact['name']
            if fact['category']:
                activity = '%s@%s' % (activity, fact['category'])

            tags = fact["tags"]
            if fact["description"]:
                tags.append(fact["description"])

            runtime.storage.add_fact(activity, ", ".join(tags))
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
        self.update_label()

    def after_fact_update(self, event, date):
        self.load_day()
        self.update_label()
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

    """global shortcuts"""
    def on_keybinding_activated(self, event, data):
        self.__show_toggle(None, not self.button.get_active())


    def on_conf_changed(self, event, data):
        key, value = data
        
        if key == "enable_timeout":
            self.timeout_enabled = value
        elif key == "notify_on_idle":
            self.notify_on_idle = value
        elif key == "notify_interval":
            if PYNOTIFY and 0 < value < 121:
                self.notify_interval = value
            else:
                self.notify_interval = None
        elif key == "day_start_minutes":
            self.day_start = dt.time(value / 60, value % 60)
            self.load_day()
            self.update_label()
            
    def on_activity_text_changed(self, widget):
        self.get_widget("switch_activity").set_sensitive(widget.get_text() != "")

    def on_switch_activity_clicked(self, widget):
        runtime.storage.add_fact(self.new_name.get_text().decode("utf8", "replace"),
                                 self.new_tags.get_text().decode("utf8", "replace"))
        self.new_name.set_text("")
        self.new_tags.set_text("")
        runtime.dispatcher.dispatch('panel_visible', False)

    def on_stop_tracking_clicked(self, widget):
        runtime.storage.touch_fact(self.last_activity)
        self.last_activity = None
        runtime.dispatcher.dispatch('panel_visible', False)

    def show(self):
        self.window.show_all()

    def get_widget(self, name):
        return self._gui.get_object(name)
