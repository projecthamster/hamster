# - coding: utf-8 -

# Copyright (C) 2008-2009 Toms Bauģis <toms.baugis at gmail.com>

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

from ..lib import stuff
from ..configuration import load_ui_file

import gtk, gobject, pango
import datetime as dt
import calendar
import gobject
import re

class RangePick(gtk.ToggleButton):
    """ a text entry widget with calendar popup"""
    __gsignals__ = {
        # day|week|month|manual, start, end
        'range-selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
    }


    def __init__(self, date = None):
        gtk.ToggleButton.__init__(self)

        self._gui = load_ui_file("range_pick.ui")
        self.popup = self.get_widget("range_popup")

        hbox = gtk.HBox()
        hbox.set_spacing(3)
        self.label = gtk.Label()
        hbox.pack_start(self.label, False)
        #self.get_widget("hbox1").pack_start(gtk.VSeparator())
        hbox.pack_start(gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_ETCHED_IN), False)
        self.add(hbox)

        self.start_date, self.end_date, self.view_date = None, None, None

        self.popup.connect("focus-out-event", self.on_focus_out)
        self.connect("toggled", self.on_toggle)

        self._gui.connect_signals(self)
        self.connect("destroy", self.on_destroy)

    def on_destroy(self, window):
        self.popup.destroy()
        self.popup = None
        self._gui = None

    def on_toggle(self, button):
        if self.get_active():
            self.show()
        else:
            self.hide()

    def set_range(self, start_date, end_date, view_date):
        self.start_date, self.end_date, self.view_date = start_date, end_date, view_date
        self.label.set_markup('<big><b>%s</b></big>' % stuff.format_range(start_date, end_date).encode("utf-8"))

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def on_focus_out(self, window, event):
        # avoid double-toggling when focus goes from window to the toggle button
        if gtk.STATE_PRELIGHT & self.get_state():
            return

        self.set_active(False)



    def hide(self):
        self.set_active(False)
        self.popup.hide()

    def show(self):
        x, y = self.get_window().get_origin()

        alloc = self.get_allocation()

        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)

        self.get_widget("day_preview").set_text(stuff.format_range(self.view_date, self.view_date).decode("utf-8"))
        self.get_widget("week_preview").set_text(stuff.format_range(*stuff.week(self.view_date)).decode("utf-8"))
        self.get_widget("month_preview").set_text(stuff.format_range(*stuff.month(self.view_date)).decode("utf-8"))

        start_cal = self.get_widget("start_calendar")
        start_cal.select_month(self.start_date.month - 1, self.start_date.year)
        start_cal.select_day(self.start_date.day)

        end_cal = self.get_widget("end_calendar")
        end_cal.select_month(self.end_date.month - 1, self.end_date.year)
        end_cal.select_day(self.end_date.day)

        self.popup.show_all()
        self.get_widget("day").grab_focus()
        self.set_active(True)

    def emit_range(self, range, start, end):
        self.hide()
        self.emit("range-selected", range, start, end)

    def on_day_clicked(self, button):
        self.emit_range("day", self.view_date, self.view_date)

    def on_week_clicked(self, button):
        self.start_date, self.end_date = stuff.week(self.view_date)
        self.emit_range("week", self.start_date, self.end_date)

    def on_month_clicked(self, button):
        self.start_date, self.end_date = stuff.month(self.view_date)
        self.emit_range("month", self.start_date, self.end_date)

    def on_manual_range_apply_clicked(self, button):
        self.current_range = "manual"
        cal_date = self.get_widget("start_calendar").get_date()
        self.start_date = dt.date(cal_date[0], cal_date[1] + 1, cal_date[2])

        cal_date = self.get_widget("end_calendar").get_date()
        self.end_date = dt.date(cal_date[0], cal_date[1] + 1, cal_date[2])

        # make sure we always have a valid range
        if self.end_date < self.start_date:
            self.start_date, self.end_date = self.end_date, self.start_date

        self.emit_range("manual", self.start_date, self.end_date)
