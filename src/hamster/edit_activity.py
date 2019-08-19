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
from textwrap import dedent
import time
import datetime as dt

""" TODO: hook into notifications and refresh our days if some evil neighbour
          edit fact window has dared to edit facts
"""
from hamster import widgets
from hamster.lib.configuration import runtime, conf, load_ui_file
from hamster.lib.stuff import hamster_today, hamster_now, escape_pango
from hamster.lib import Fact


class CustomFactController(gobject.GObject):
    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self,  parent=None, fact_id=None, base_fact=None):
        gobject.GObject.__init__(self)

        self._gui = load_ui_file("edit_activity.ui")
        self.window = self.get_widget('custom_fact_window')
        self.window.set_size_request(600, 200)
        self.parent = parent
        # None if creating a new fact, instead of editing one
        self.fact_id = fact_id

        self.activity = widgets.ActivityEntry()
        self.activity.connect("changed", self.on_activity_changed)
        self.get_widget("activity_box").add(self.activity)

        self.day_start = conf.day_start

        self.dayline = widgets.DayLine()
        self._gui.get_object("day_preview").add(self.dayline)

        self.description_box = self.get_widget('description')

        self.activity.grab_focus()
        if fact_id:
            # editing
            fact = runtime.storage.get_fact(fact_id)
            self.date = fact.date
            original_fact = fact
            self.get_widget("save_button").set_label("gtk-save")
            self.window.set_title(_("Update activity"))
        else:
            self.date = hamster_today()
            self.get_widget("delete_button").set_sensitive(False)
            if base_fact:
                # cloning
                original_fact = base_fact.copy()
                # start running now.
                # Do not try to pass end_time=None to copy(), above;
                # it would be discarded.
                original_fact.start_time = hamster_now()
                original_fact.end_time = None
            else:
                original_fact = None

        if original_fact:
            stripped_fact = original_fact.copy()
            stripped_fact.description = None
            label = stripped_fact.serialized(prepend_date=False)
            with self.activity.handler_block(self.activity.checker):
                self.activity.set_text(label)
                time_len = len(label) - len(stripped_fact.serialized_name())
                self.activity.select_region(0, time_len - 1)
            buf = gtk.TextBuffer()
            buf.set_text(original_fact.description or "")
            self.description_box.set_buffer(buf)

        self.activity.original_fact = original_fact

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
        day_facts = runtime.storage.get_facts(self.date, ongoing_days=31)
        self.dayline.plot(self.date, day_facts, start_time, end_time)

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def show(self):
        self.window.show()

    def figure_description(self):
        buf = self.description_box.get_buffer()
        description = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), 0)
        return description.strip()

    def localized_fact(self):
        """Make sure fact has the correct start_time."""
        fact = Fact(self.activity.get_text())
        if fact.start_time:
            fact.date = self.date
        else:
            fact.start_time = hamster_now()
        return fact

    def on_save_button_clicked(self, button):
        fact = self.validate_fields()
        if self.fact_id:
            runtime.storage.update_fact(self.fact_id, fact)
        else:
            runtime.storage.add_fact(fact)
        self.close_window()

    def on_activity_changed(self, combo):
        self.validate_fields()

    def update_status(self, looks_good, markup):
        """Set icon image and markup."""
        if looks_good:
            icon_name = "dialog-ok"
        else:
            icon_name = "dialog-error"
        position = gtk.EntryIconPosition.SECONDARY
        self.activity.set_icon_from_icon_name(position, icon_name)
        self.activity.set_icon_tooltip_markup(position, markup)
        self.get_widget("save_button").set_sensitive(looks_good)

    def validate_fields(self):
        """Check entry and description validity.

        Return the consolidated fact if successful, or None.
        """
        fact = self.localized_fact()

        now = hamster_now()
        self.get_widget("button-next-day").set_sensitive(self.date < now.date())

        if self.date != now.date():
            now = dt.datetime.combine(self.date, now.time())

        self.draw_preview(fact.start_time or now,
                          fact.end_time or now)

        if fact.start_time is None:
            self.update_status(looks_good=False, markup="Missing start time")
            return None

        if fact.activity is None:
            self.update_status(looks_good=False, markup="Missing activity")
            return None

        description_box_content = self.figure_description()
        if fact.description and description_box_content:
            escaped_cmd = escape_pango(fact.description)
            escaped_box = escape_pango(description_box_content)
            tooltip = dedent("""\
                             <b>Duplicate description</b>
                             <i>command line</i>:
                             '{}'
                             <i>description box</i>:
                             '''{}'''
                             """).format(escaped_cmd, escaped_box)
            print(dedent(tooltip))
            self.update_status(looks_good=False,
                               markup=tooltip)
            return None

        # Good to go, no ambiguity
        if description_box_content:
            fact.description = description_box_content
        self.update_status(looks_good=True, markup="")
        return fact

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
            if self.description_box.has_focus():
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
