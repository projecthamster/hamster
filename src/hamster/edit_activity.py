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
        self.description_buffer = self.description_box.get_buffer()
        self.description_buffer.connect("changed", self.on_description_changed)

        self.save_button = self.get_widget("save_button")

        self.activity.grab_focus()
        if fact_id:
            # editing
            fact = runtime.storage.get_fact(fact_id)
            self.date = fact.date
            original_fact = fact
            self.window.set_title(_("Update activity"))
        else:
            self.date = hamster_today()
            self.get_widget("delete_button").set_sensitive(False)
            if base_fact:
                # start a clone now.
                original_fact = base_fact.copy(start_time=hamster_now(),
                                               end_time=None)
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
            self.description_buffer.set_text(original_fact.description or "")

        self.activity.original_fact = original_fact

        self._gui.connect_signals(self)
        self.validate_fields()
        self.window.show_all()

    def on_description_changed(self, text):
        self.validate_fields()

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
        buf = self.description_buffer
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

    def update_status(self, status, markup):
        """Set save button sensitivity and tooltip."""
        self.save_button.set_tooltip_markup(markup)
        if status == "looks good":
            self.save_button.set_label("gtk-save")
            self.save_button.set_sensitive(True)
        elif status == "warning":
            self.save_button.set_label("gtk-dialog-warning")
            self.save_button.set_sensitive(True)
        elif status == "wrong":
            self.save_button.set_label("gtk-save")
            self.save_button.set_sensitive(False)
        else:
            raise ValueError("unknown status: '{}'".format(status))

    def validate_fields(self):
        """Check fields information.

        Update gui status about entry and description validity.
        Try to merge date, activity and description informations.

        Return the consolidated fact if successful, or None.
        """
        fact = self.localized_fact()

        now = hamster_now()
        self.get_widget("button-next-day").set_sensitive(self.date < now.date())

        if self.date == now.date():
            default_dt = now
        else:
            default_dt = dt.datetime.combine(self.date, now.time())

        self.draw_preview(fact.start_time or default_dt,
                          fact.end_time or default_dt)

        if fact.start_time is None:
            self.update_status(status="wrong", markup="Missing start time")
            return None

        if not fact.activity:
            self.update_status(status="wrong", markup="Missing activity")
            return None

        description_box_content = self.figure_description()
        if fact.description and description_box_content:
            escaped_cmd = escape_pango(fact.description)
            escaped_box = escape_pango(description_box_content)
            markup = dedent("""\
                             <b>Duplicate description</b>
                             <i>command line</i>:
                             '{}'
                             <i>description box</i>:
                             '''{}'''
                             """).format(escaped_cmd, escaped_box)
            self.update_status(status="wrong",
                               markup=markup)
            return None

        # Good to go, no description ambiguity
        if description_box_content:
            fact.description = description_box_content

        if (fact.delta < dt.timedelta(0)) and fact.end_time:
            fact.end_time += dt.timedelta(days=1)
            markup = dedent("""\
                            <b>Working late ?</b>
                            Duration would be negative.
                            This happens when the activity crosses the
                            hamster day start time ({:%H:%M} from tracking settings).

                            Changing the end time date to the next day.
                            Pressing the button would save
                            an actvity going from
                            {}
                            to
                            {}
                            (in civil local time)
                            """.format(conf.day_start, fact.start_time, fact.end_time))
            self.update_status(status="warning", markup=markup)
            return fact

        # nothing unusual
        self.update_status(status="looks good", markup="")
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
