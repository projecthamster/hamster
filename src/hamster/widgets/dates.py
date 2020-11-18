# - coding: utf-8 -

# Copyright (C) 2008-2009, 2014 Toms Bauģis <toms.baugis at gmail.com>

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
from gi.repository import Pango as pango

import calendar
import re

from hamster.lib import datetime as dt
from hamster.lib import stuff
from hamster.lib.configuration import load_ui_file


class Calendar():
    """Python date interface to a Gtk.Calendar.

    widget (Gtk.Calendar):
        the associated Gtk widget.
    expander (Gtk.expander):
        An optional expander which contains the widget.
        The expander label displays the date.
    """
    def __init__(self, widget, expander=None):
        self.widget = widget
        self.expander = expander
        self.widget.connect("day-selected", self.on_date_changed)

    @property
    def date(self):
        """Selected day, as datetime.date."""
        year, month, day = self.widget.get_date()
        # months start at 0 in Gtk.Calendar and at 1 in python date
        month += 1
        return dt.date(year=year, month=month, day=day) if day else None

    @date.setter
    def date(self, value):
        """Set date.

        value can be a python date or datetime.
        """
        if value is None:
            # unselect day
            self.widget.select_day(0)
        else:
            year = value.year
            # months start at 0 in Gtk.Calendar and at 1 in python date
            month = value.month - 1
            day = value.day
            self.widget.select_month(month, year)
            self.widget.select_day(day)

    def on_date_changed(self, widget):
        if self.expander:
            if self.date:
                self.expander.set_label(self.date.strftime("%A %Y-%m-%d"))
            else:
                self.expander.set_label("")

    def __getattr__(self, name):
        return getattr(self.widget, name)


class RangePick(gtk.ToggleButton):
    """ a text entry widget with calendar popup"""
    __gsignals__ = {
        # day|week|month|manual, start, end
        'range-selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
    }


    def __init__(self, today):
        gtk.ToggleButton.__init__(self)

        self._ui = load_ui_file("date_range.ui")

        self.popup = self.get_widget("range_popup")
        self.popup.set_relative_to(self)

        self.today = today

        hbox = gtk.HBox()
        hbox.set_spacing(3)
        self.label = gtk.Label()
        hbox.add(self.label)
        hbox.add(gtk.Arrow(gtk.ArrowType.DOWN, gtk.ShadowType.ETCHED_IN))
        self.add(hbox)

        self.start_date, self.end_date = None, None
        self.current_range = None

        self.popup.connect("closed", self.on_closed)
        self.connect("toggled", self.on_toggle)

        self._ui.connect_signals(self)
        self.connect("destroy", self.on_destroy)

    def on_destroy(self, window):
        self.popup.destroy()
        self.popup = None
        self._ui = None

    def on_toggle(self, button):
        if self.get_active():
            self.show()
        else:
            self.hide()


    def set_range(self, start_date, end_date=None):
        end_date = end_date or start_date
        self.start_date, self.end_date = start_date, end_date
        self.label.set_markup('<b>%s</b>' % stuff.format_range(start_date, end_date))

    def get_range(self):
        return self.start_date, self.end_date

    def emit_range(self, range, start, end):
        self.set_range(start, end)
        self.emit("range-selected", range, start, end)
        self.hide()


    def prev_range(self):
        start, end = self.start_date, self.end_date

        if self.current_range == "day":
            start, end = start - dt.timedelta(1), end - dt.timedelta(1)
        elif self.current_range == "week":
            start, end = start - dt.timedelta(7), end - dt.timedelta(7)
        elif self.current_range == "month":
            end = start - dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(end.year, end.month)
            start = end - dt.timedelta(days_in_month - 1)
        else:
            # manual range - just jump to the next window
            days =  (end - start) + dt.timedelta(days = 1)
            start = start - days
            end = end - days
        self.emit_range(self.current_range, start, end)


    def next_range(self):
        start, end = self.start_date, self.end_date

        if self.current_range == "day":
            start, end = start + dt.timedelta(1), end + dt.timedelta(1)
        elif self.current_range == "week":
            start, end = start + dt.timedelta(7), end + dt.timedelta(7)
        elif self.current_range == "month":
            start = end + dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(start.year, start.month)
            end = start + dt.timedelta(days_in_month - 1)
        else:
            # manual range - just jump to the next window
            days =  (end - start) + dt.timedelta(days = 1)
            start = start + days
            end = end + days

        self.emit_range(self.current_range, start, end)



    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._ui.get_object(name)


    def on_closed(self, popup):
        self.set_active(False)


    def hide(self):
        self.set_active(False)
        self.popup.hide()

    def show(self):
        self.get_widget("day_preview").set_text(stuff.format_range(self.today, self.today))
        self.get_widget("week_preview").set_text(stuff.format_range(*stuff.week(self.today)))
        self.get_widget("month_preview").set_text(stuff.format_range(*stuff.month(self.today)))

        start_cal = self.get_widget("start_calendar")
        start_cal.select_month(self.start_date.month - 1, self.start_date.year)
        start_cal.select_day(self.start_date.day)

        end_cal = self.get_widget("end_calendar")
        end_cal.select_month(self.end_date.month - 1, self.end_date.year)
        end_cal.select_day(self.end_date.day)

        self.popup.popup()
        self.get_widget("day").grab_focus()
        self.set_active(True)


    def on_day_clicked(self, button):
        self.current_range = "day"
        self.emit_range("day", self.today, self.today)

    def on_week_clicked(self, button):
        self.current_range = "week"
        self.start_date, self.end_date = stuff.week(self.today)
        self.emit_range("week", self.start_date, self.end_date)

    def on_month_clicked(self, button):
        self.current_range = "month"
        self.start_date, self.end_date = stuff.month(self.today)
        self.emit_range("month", self.start_date, self.end_date)

    def on_manual_range_apply_clicked(self, button):
        self.current_range = "manual"
        # GtkCalendar January is 0, hence the + 1
        year, month, day = self.get_widget("start_calendar").get_date()
        self.start_date = dt.date(year, month + 1, day)

        year, month, day = self.get_widget("end_calendar").get_date()
        self.end_date = dt.date(year, month + 1, day)

        # make sure we always have a valid range
        if self.end_date < self.start_date:
            self.start_date, self.end_date = self.end_date, self.start_date

        self.emit_range("manual", self.start_date, self.end_date)
