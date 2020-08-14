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

""" TODO: hook into notifications and refresh our days if some evil neighbour
          edit fact window has dared to edit facts
"""
from hamster import widgets
from hamster.lib import datetime as dt
from hamster.lib.configuration import Controller, runtime, load_ui_file
from hamster.lib.fact import Fact, FactError
from hamster.lib.stuff import escape_pango



class CustomFactController(Controller):
    """Controller for a Fact edition window.

    Args:
        action (str): "add", "clone", "edit"
        fact_id (int): used for "clone" and "edit"
    """

    def __init__(self, action, fact_id=None):
        Controller.__init__(self)

        self._date = None  # for the date property

        self._gui = load_ui_file("edit_activity.ui")
        self.window = self.get_widget('custom_fact_window')
        self.window.set_size_request(600, 200)


        self.action = action
        self.fact_id = fact_id

        self.category_entry = widgets.CategoryEntry(widget=self.get_widget('category'))
        self.activity_entry = widgets.ActivityEntry(widget=self.get_widget('activity'),
                                                    category_widget=self.category_entry)

        self.cmdline = widgets.CmdLineEntry(parent=self.get_widget("cmdline box"))
        self.cmdline.connect("focus_in_event", self.on_cmdline_focus_in_event)
        self.cmdline.connect("focus_out_event", self.on_cmdline_focus_out_event)

        self.dayline = widgets.DayLine()
        self._gui.get_object("day_preview").add(self.dayline)

        self.description_box = self.get_widget('description')
        self.description_buffer = self.description_box.get_buffer()

        self.end_date = widgets.Calendar(widget=self.get_widget("end date"),
                                         expander=self.get_widget("end date expander"))

        self.end_time = widgets.TimeInput(parent=self.get_widget("end time box"))

        self.start_date = widgets.Calendar(widget=self.get_widget("start date"),
                                           expander=self.get_widget("start date expander"))

        self.start_time = widgets.TimeInput(parent=self.get_widget("start time box"))

        self.tags_entry = widgets.TagsEntry()
        self.get_widget("tags box").add(self.tags_entry)

        self.save_button = self.get_widget("save_button")

        # this will set self.master_is_cmdline
        self.cmdline.grab_focus()

        title = _("Update activity") if action == "edit" else _("Add activity")
        self.window.set_title(title)
        self.get_widget("delete_button").set_sensitive(action == "edit")
        if action == "edit":
            self.fact = runtime.storage.get_fact(fact_id)
        elif action == "clone":
            base_fact = runtime.storage.get_fact(fact_id)
            self.fact = base_fact.copy(start_time=dt.datetime.now(),
                                       end_time=None)
        else:
            self.fact = Fact(start_time=dt.datetime.now())

        original_fact = self.fact
        # TODO: should use hday, not date.
        self.date = self.fact.date

        self.update_fields()
        self.update_cmdline(select=True)

        self.cmdline.original_fact = original_fact

        # This signal should be emitted only after a manual modification,
        # not at init time when cmdline might not always be fully parsable.
        self.cmdline.connect("changed", self.on_cmdline_changed)
        self.description_buffer.connect("changed", self.on_description_changed)
        self.start_time.connect("changed", self.on_start_time_changed)
        self.start_date.connect("day-selected", self.on_start_date_changed)
        self.start_date.expander.connect("activate",
                                         self.on_start_date_expander_activated)
        self.end_time.connect("changed", self.on_end_time_changed)
        self.end_date.connect("day-selected", self.on_end_date_changed)
        self.end_date.expander.connect("activate",
                                         self.on_end_date_expander_activated)
        self.activity_entry.connect("changed", self.on_activity_changed)
        self.category_entry.connect("changed", self.on_category_changed)
        self.tags_entry.connect("changed", self.on_tags_changed)

        self._gui.connect_signals(self)
        self.validate_fields()
        self.window.show_all()

    @property
    def date(self):
        """Default hamster day."""
        return self._date

    @date.setter
    def date(self, value):
        self._date = value
        self.cmdline.default_day = value

    def on_prev_day_clicked(self, button):
        self.increment_date(-1)

    def on_next_day_clicked(self, button):
        self.increment_date(+1)

    def draw_preview(self, start_time, end_time=None):
        day_facts = runtime.storage.get_facts(self.date)
        self.dayline.plot(self.date, day_facts, start_time, end_time)

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def increment_date(self, days):
        delta = dt.timedelta(days=days)
        self.change_start_date(self.date + delta)
        self.update_fields()

    def show(self):
        self.window.show()

    def figure_description(self):
        buf = self.description_buffer
        description = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), 0)
        return description.strip()

    def on_activity_changed(self, widget):
        if not self.master_is_cmdline:
            self.fact.activity = self.activity_entry.get_text()
            self.validate_fields()
            self.update_cmdline()

    def on_category_changed(self, widget):
        if not self.master_is_cmdline:
            self.fact.category = self.category_entry.get_text()
            self.validate_fields()
            self.update_cmdline()

    def on_cmdline_changed(self, widget):
        if self.master_is_cmdline:
            fact = Fact.parse(self.cmdline.get_text(), default_day=self.date)
            previous_cmdline_fact = self.cmdline_fact
            # copy the entered fact before any modification
            self.cmdline_fact = fact.copy()
            if fact.start_time is None:
                fact.start_time = dt.datetime.now()
            if fact.description == previous_cmdline_fact.description:
                # no change to description here, keep the main one
                fact.description = self.fact.description
            self.fact = fact
            self.update_fields()

    def on_cmdline_focus_in_event(self, widget, event):
        self.master_is_cmdline = True

    def on_cmdline_focus_out_event(self, widget, event):
        self.master_is_cmdline = False

    def on_description_changed(self, text):
        if not self.master_is_cmdline:
            self.fact.description = self.figure_description()
            self.validate_fields()
            self.update_cmdline()

    def on_end_date_changed(self, widget):
        if not self.master_is_cmdline:
            if self.fact.end_time:
                time = self.fact.end_time.time()
                self.fact.end_time = dt.datetime.combine(self.end_date.date, time)
                self.validate_fields()
                self.update_cmdline()
            elif self.end_date.date:
                # No end time means on-going, hence date would be meaningless.
                # And a default end date may be provided when end time is set,
                # so there should never be a date without time.
                self.end_date.date = None

    def on_end_date_expander_activated(self, widget):
        # state has not changed yet, toggle also start_date calendar visibility
        previous_state = self.end_date.expander.get_expanded()
        self.start_date.expander.set_expanded(not previous_state)

    def on_end_time_changed(self, widget):
        if not self.master_is_cmdline:
            # self.end_time.start_time() was given a datetime,
            # so self.end_time.time is a datetime too.
            end = self.end_time.time
            self.fact.end_time = end
            self.end_date.date = end.date() if end else None
            self.validate_fields()
            self.update_cmdline()

    def on_start_date_changed(self, widget):
        if not self.master_is_cmdline:
            new_date = self.start_date.date
            self.change_start_date(new_date)

    def change_start_date(self, new_date):
        if self.fact.start_time:
            previous_date = self.fact.start_time.date()
            delta = new_date - previous_date
            self.fact.start_time += delta
            if self.fact.end_time:
                # preserve fact duration
                self.fact.end_time += delta
                self.end_date.date = self.fact.end_time
        self.date = self.fact.date or dt.hday.today()
        self.validate_fields()
        self.update_cmdline()

    def on_start_date_expander_activated(self, widget):
        # state has not changed yet, toggle also end_date calendar visibility
        previous_state = self.start_date.expander.get_expanded()
        self.end_date.expander.set_expanded(not previous_state)

    def on_start_time_changed(self, widget):
        if not self.master_is_cmdline:
            # note: resist the temptation to preserve duration here;
            # for instance, end time might be at the beginning of next fact.
            new_time = self.start_time.time
            if new_time:
                if self.fact.start_time:
                    new_start_time = dt.datetime.combine(self.fact.start_time.date(),
                                                         new_time)
                else:
                    # date not specified; result must fall in current hamster_day
                    new_start_time = dt.datetime.from_day_time(dt.hday.today(), new_time)
            else:
                new_start_time = None
            self.fact.start_time = new_start_time
            # let start_date extract date or handle None
            self.start_date.date = new_start_time
            self.validate_fields()
            self.update_cmdline()

    def on_tags_changed(self, widget):
        if not self.master_is_cmdline:
            self.fact.tags = self.tags_entry.get_tags()
            self.update_cmdline()

    def present(self):
        self.window.present()

    def update_cmdline(self, select=None):
        """Update the cmdline entry content."""
        self.cmdline_fact = self.fact.copy(description=None)
        label = self.cmdline_fact.serialized(default_day=self.date)
        with self.cmdline.handler_block(self.cmdline.checker):
            self.cmdline.set_text(label)
            if select:
                # select the range string exactly (without separator)
                __, rest = dt.Range.parse(label, position="head", separator="")
                self.cmdline.select_region(0, len(label) - len(rest))

    def update_fields(self):
        """Update gui fields content."""
        self.start_time.time = self.fact.start_time
        self.end_time.time = self.fact.end_time
        self.end_time.set_start_time(self.fact.start_time)
        self.start_date.date = self.fact.date or self.date
        self.end_date.date = self.fact.date or self.date
        self.activity_entry.set_text(self.fact.activity)
        self.category_entry.set_text(self.fact.category)
        self.description_buffer.set_text(self.fact.description)
        self.tags_entry.set_tags(self.fact.tags)
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
        fact = self.fact

        now = dt.datetime.now()
        self.get_widget("button-next-day").set_sensitive(self.date < now.date())

        if self.date == now.date():
            default_dt = now
        else:
            default_dt = dt.datetime.combine(self.date, now.time())

        self.draw_preview(fact.start_time or default_dt,
                          fact.end_time or default_dt)

        try:
            runtime.storage.check_fact(fact, default_day=self.date)
        except FactError as error:
            self.update_status(status="wrong", markup=str(error))
            return None

        roundtrip_fact = Fact.parse(fact.serialized(), default_day=self.date)
        if roundtrip_fact != fact:
            self.update_status(status="wrong", markup="Fact could not be parsed back")
            return None

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

    def on_save_button_clicked(self, button):
        if self.action == "edit":
            runtime.storage.update_fact(self.fact_id, self.fact)
        else:
            runtime.storage.add_fact(self.fact)
        self.close_window()

    def on_window_key_pressed(self, tree, event_key):
        popups = (self.cmdline.popup.get_property("visible")
                  or self.start_time.popup.get_property("visible")
                  or self.end_time.popup.get_property("visible")
                  or self.tags_entry.popup.get_property("visible"))

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
            if self.validate_fields():
                self.on_save_button_clicked(None)
