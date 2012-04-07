# -*- coding: utf-8 -*-

# Copyright (C) 2007-2009 Toms Bauģis <toms.baugis at gmail.com>

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

import gtk, gobject
import time
import datetime as dt

""" TODO: hook into notifications and refresh our days if some evil neighbour
          edit fact window has dared to edit facts
"""
import widgets
from configuration import runtime, conf, load_ui_file
from lib import stuff

class CustomFactController(gtk.Object):
    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self,  parent = None, fact_date = None, fact_id = None):
        gtk.Object.__init__(self)

        self._gui = load_ui_file("edit_activity.ui")
        self.window = self.get_widget('custom_fact_window')

        self.parent, self.fact_id = parent, fact_id
        start_date, end_date = None, None

        #TODO - should somehow hint that time is not welcome here
        self.new_name = widgets.ActivityEntry()
        self.get_widget("activity_box").add(self.new_name)

        self.new_tags = widgets.TagsEntry()
        self.get_widget("tags_box").add(self.new_tags)

        day_start = conf.get("day_start_minutes")
        self.day_start = dt.time(day_start / 60, day_start % 60)

        if fact_id:
            fact = runtime.storage.get_fact(fact_id)

            label = fact.activity
            if fact.category != _("Unsorted"):
                label += "@%s" %  fact.category

            self.new_name.set_text(label)

            self.new_tags.set_text(", ".join(fact.tags))


            start_date = fact.start_time
            end_date = fact.end_time

            buf = gtk.TextBuffer()
            buf.set_text(fact.description or "")
            self.get_widget('description').set_buffer(buf)

            self.get_widget("save_button").set_label("gtk-save")
            self.window.set_title(_("Update activity"))
        else:
            self.get_widget("delete_button").set_sensitive(False)

            # if there is previous activity with end time - attach to it
            # otherwise let's start at 8am (unless it is today - in that case
            # we will assume that the user wants to start from this moment)
            fact_date = fact_date or dt.date.today()
            if fact_date > dt.date.today():
                fact_date = dt.date.today()

            last_activity = runtime.storage.get_facts(fact_date)
            if last_activity and last_activity[-1].end_time:
                start_date = last_activity[-1].end_time

                if fact_date != dt.date.today():
                    end_date = start_date + dt.timedelta(minutes=30)
            else:
                if fact_date == dt.date.today():
                    start_date = dt.datetime.now()
                else:
                    start_date = dt.datetime(fact_date.year, fact_date.month,
                                             fact_date.day, 8)


        if not end_date:
            self.get_widget("in_progress").set_active(True)
            if (dt.datetime.now() - start_date).days == 0:
                end_date = dt.datetime.now()


        start_date = start_date or dt.datetime.now()
        end_date = end_date or start_date + dt.timedelta(minutes = 30)


        self.start_date = widgets.DateInput(start_date)
        self.get_widget("start_date_placeholder").add(self.start_date)

        self.start_time = widgets.TimeInput(start_date)
        self.get_widget("start_time_placeholder").add(self.start_time)

        self.end_time = widgets.TimeInput(end_date, start_date)
        self.get_widget("end_time_placeholder").add(self.end_time)
        self.set_end_date_label(end_date)


        self.dayline = widgets.DayLine()
        self.dayline.connect("on-time-chosen", self.update_time)
        self._gui.get_object("day_preview").add(self.dayline)

        self.on_in_progress_toggled(self.get_widget("in_progress"))

        self.start_date.connect("date-entered", self.on_start_date_entered)
        self.start_time.connect("time-entered", self.on_start_time_entered)
        self.new_name.connect("changed", self.on_new_name_changed)
        self.end_time.connect("time-entered", self.on_end_time_entered)
        self._gui.connect_signals(self)

        self.window.show_all()

    def update_time(self, widget, start_time, end_time):
        self.start_time.set_time(start_time)
        self.on_start_time_entered(None)

        self.start_date.set_date(start_time)

        self.get_widget("in_progress").set_active(end_time is None)

        if end_time:
            if end_time > dt.datetime.now():
                end_time = dt.datetime.now()

            self.end_time.set_time(end_time)
            self.set_end_date_label(end_time)

        self.draw_preview(start_time, end_time)


    def draw_preview(self, start_time, end_time = None):

        view_date = (start_time - dt.timedelta(hours = self.day_start.hour,
                                              minutes = self.day_start.minute)).date()

        day_facts = runtime.storage.get_facts(view_date)
        self.dayline.plot(view_date, day_facts, start_time, end_time)

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


    def _get_datetime(self, prefix):
        start_time = self.start_time.get_time()
        start_date = self.start_date.get_date()

        if prefix == "end":
            end_time = self.end_time.get_time()
            end_date = start_date
            if end_time < start_time:
                end_date = start_date + dt.timedelta(days=1)

            if end_date:
                self.set_end_date_label(end_date)
            time, date = end_time, end_date
        else:
            time, date = start_time, start_date

        if time is not None and date:
            return dt.datetime.combine(date, time)
        else:
            return None

    def on_save_button_clicked(self, button):
        activity_name, temporary = self.new_name.get_value()

        if self.get_widget("in_progress").get_active():
            end_time = None
        else:
            end_time = self._get_datetime("end")

        fact = stuff.Fact(activity_name,
                          description = self.figure_description(),
                          tags = self.new_tags.get_text().decode('utf8'),
                          start_time = self._get_datetime("start"),
                          end_time = end_time)
        if not fact.activity:
            return False

        if self.fact_id:
            runtime.storage.update_fact(self.fact_id, fact, temporary)
        else:
            runtime.storage.add_fact(fact, temporary)

        self.close_window()

    def on_delete_clicked(self, button):
        runtime.storage.remove_fact(self.fact_id)
        self.close_window()

    def on_activity_list_key_pressed(self, entry, event):
        #treating tab as keydown to be able to cycle through available values
        if event.keyval == gtk.keysyms.Tab:
            event.keyval = gtk.keysyms.Down
        return False

    def on_in_progress_toggled(self, check):
        sensitive = not check.get_active()
        self.end_time.set_sensitive(sensitive)
        self.get_widget("end_label").set_sensitive(sensitive)
        self.get_widget("end_date_label").set_sensitive(sensitive)
        self.validate_fields()

    def on_cancel_clicked(self, button):
        self.close_window()

    def on_new_name_changed(self, combo):
        self.validate_fields()

    def on_start_date_entered(self, widget):
        if dt.datetime.combine(self.start_date.get_date(), self.start_time.get_time()) > dt.datetime.now():
            self.start_date.set_date(dt.date.today())

            # if we are still over - push one more day back
            if dt.datetime.combine(self.start_date.get_date(), self.start_time.get_time()) > dt.datetime.now():
                self.start_date.set_date(dt.date.today() - dt.timedelta(days=1))

        self.validate_fields()

    def on_start_time_entered(self, widget):
        start_time = self.start_time.get_time()

        if not start_time:
            return

        if dt.datetime.combine(self.start_date.get_date(), start_time) > dt.datetime.now():
            self.start_date.set_date(dt.date.today() - dt.timedelta(days=1))


        self.end_time.set_start_time(start_time)
        self.validate_fields()

    def on_end_time_entered(self, widget):
        self.validate_fields()

    def set_end_date_label(self, some_date):
        self.get_widget("end_date_label").set_text(some_date.strftime("%x"))

    def validate_fields(self, widget = None):
        activity_text, temporary = self.new_name.get_value()
        start_time = self._get_datetime("start")

        if self.get_widget("in_progress").get_active():
            end_time = None
        else:
            end_time = self._get_datetime("end")
            if end_time > dt.datetime.now():
                end_time = dt.datetime.now()

            # make sure we are within 24 hours of start time
            end_time -= dt.timedelta(days=(end_time - start_time).days)

            self.end_time.set_time(end_time)

        self.draw_preview(start_time, end_time)

        looks_good = activity_text is not None and start_time \
                     and (not end_time or (end_time - start_time).days == 0)


        self.get_widget("save_button").set_sensitive(looks_good)
        return looks_good

    def on_window_key_pressed(self, tree, event_key):
        if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w
              and event_key.state & gtk.gdk.CONTROL_MASK)):

            if self.start_date.popup.get_property("visible") or \
               self.start_time.popup.get_property("visible") or \
               self.end_time.popup.get_property("visible") or \
               self.new_name.popup.get_property("visible") or \
               self.new_tags.popup.get_property("visible"):
                return False

            self.close_window()

    def on_close(self, widget, event):
        self.close_window()

    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            self.window = None
            self._gui = None
            self.emit("on-close")
