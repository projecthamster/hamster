# -*- coding: utf-8 -*-

# Copyright (C) 2007-2009, 2014 Toms Bauģis <toms.baugis at gmail.com>

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

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
import time
import datetime as dt

""" TODO: hook into notifications and refresh our days if some evil neighbour
          edit fact window has dared to edit facts
"""
import widgets
from hamster.lib.configuration import runtime, conf, load_ui_file
from lib import Fact

class CustomFactController(gobject.GObject):
    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self,  parent=None, fact_date=None, fact_id=None):
        gobject.GObject.__init__(self)

        self._gui = load_ui_file("edit_activity.ui")
        self.window = self.get_widget('custom_fact_window')
        self.window.set_size_request(600, 200)
        self.parent, self.fact_id = parent, fact_id

        #TODO - should somehow hint that time is not welcome here
        self.activity = widgets.ActivityEntry()
        self.activity.connect("changed", self.on_activity_changed)
        self.get_widget("activity_box").add(self.activity)

        day_start = conf.get("day_start_minutes")
        self.day_start = dt.time(day_start / 60, day_start % 60)

        self.date = fact_date
        if not self.date:
            self.date = (dt.datetime.now() - dt.timedelta(hours=self.day_start.hour,
                                                          minutes=self.day_start.minute)).date()


        self.dayline = widgets.DayLine()
        self._gui.get_object("day_preview").add(self.dayline)

        self.activity.grab_focus()
        if fact_id:
            fact = runtime.storage.get_fact(fact_id)
            label = fact.start_time.strftime("%H:%M")
            if fact.end_time:
                label += fact.end_time.strftime(" %H:%M")

            label += " " + fact.serialized_name()
            with self.activity.handler_block(self.activity.checker):
                self.activity.set_text(label)
                self.activity.select_region(len(label) - len(fact.serialized_name()), -1)


            buf = gtk.TextBuffer()
            buf.set_text(fact.description or "")
            self.get_widget('description').set_buffer(buf)

            self.get_widget("save_button").set_label("gtk-save")
            self.window.set_title(_("Update activity"))

        else:
            self.get_widget("delete_button").set_sensitive(False)


        self._gui.connect_signals(self)
        self.validate_fields()
        self.window.show_all()

    def on_prev_day_clicked(self, button):
        self.date = self.date - dt.timedelta(days=1)
        self.validate_fields()

    def on_next_day_clicked(self, button):
        self.date = self.date + dt.timedelta(days=1)
        self.validate_fields()

    def draw_preview(self, start_time, end_time=None):
        day_facts = runtime.storage.get_facts(self.date)
        self.dayline.plot(self.date, day_facts, start_time, end_time)


    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def show(self):
        self.window.show()


    def figure_description(self):
        buf = self.get_widget('description').get_buffer()
        description = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), 0)\
                         .decode("utf-8")
        return description.strip()


    def localized_fact(self):
        """makes sure fact is in our date"""
        fact = Fact(self.activity.get_text())
        if fact.start_time:
            fact.start_time = dt.datetime.combine(self.date, fact.start_time.time())

        if fact.end_time:
            fact.end_time = dt.datetime.combine(self.date, fact.end_time.time())

        return fact



    def on_save_button_clicked(self, button):
        fact = self.localized_fact()
        fact.description = self.figure_description()
        if not fact.activity:
            return False

        if self.fact_id:
            runtime.storage.update_fact(self.fact_id, fact)
        else:
            runtime.storage.add_fact(fact)

        self.close_window()

    def on_activity_changed(self, combo):
        self.validate_fields()

    def validate_fields(self, widget = None):
        fact = self.localized_fact()

        now = dt.datetime.now()
        self.get_widget("button-next-day").set_sensitive(self.date < now.date())

        if self.date != now.date():
            now = dt.datetime.combine(self.date, now.time())

        self.draw_preview(fact.start_time or now,
                          fact.end_time or now)

        looks_good = fact.activity is not None and fact.start_time is not None
        self.get_widget("save_button").set_sensitive(looks_good)
        return looks_good


    def on_delete_clicked(self, button):
        runtime.storage.remove_fact(self.fact_id)
        self.close_window()

    def on_cancel_clicked(self, button):
        self.close_window()

    def on_close(self, widget, event):
        self.close_window()

    def on_window_key_pressed(self, tree, event_key):
        popups = self.activity.popup.get_property("visible");

        if (event_key.keyval == gdk.KEY_Escape or \
           (event_key.keyval == gdk.KEY_w and event_key.state & gdk.ModifierType.CONTROL_MASK)):
            if popups:
                return False

            self.close_window()

        elif event_key.keyval in (gdk.KEY_Return, gdk.KEY_KP_Enter):
            if popups:
                return False
            if self.get_widget('description').has_focus():
                return False
            self.on_save_button_clicked(None)



    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            self.window = None
            self._gui = None
            self.emit("on-close")
