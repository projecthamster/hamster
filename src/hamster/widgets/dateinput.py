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

import gtk
import datetime as dt
import calendar
import gobject
import re

class DateInput(gtk.Entry):
    """ a text entry widget with calendar popup"""
    __gsignals__ = {
        'date-entered': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }


    def __init__(self, date = None):
        gtk.Entry.__init__(self)

        self.set_width_chars(len(dt.datetime.now().strftime("%x"))) # size to default format length
        self.date = date
        if date:
            self.set_date(date)

        self.news = False
        self.prev_cal_day = None #workaround
        self.popup = gtk.Window(type = gtk.WINDOW_POPUP)
        calendar_box = gtk.HBox()

        self.date_calendar = gtk.Calendar()
        self.date_calendar.mark_day(dt.datetime.today().day)
        self.date_calendar.connect("day-selected", self._on_day_selected)
        self.date_calendar.connect("day-selected-double-click",
                                   self.__on_day_selected_double_click)
        self.date_calendar.connect("button-press-event",
                                   self._on_cal_button_press_event)
        calendar_box.add(self.date_calendar)
        self.popup.add(calendar_box)

        self.connect("button-press-event", self._on_button_press_event)
        self.connect("key-press-event", self._on_key_press_event)
        self.connect("focus-in-event", self._on_focus_in_event)
        self.connect("focus-out-event", self._on_focus_out_event)
        self._parent_click_watcher = None # bit lame but works

        self.connect("changed", self._on_text_changed)
        self.show()
        self.connect("destroy", self.on_destroy)

    def on_destroy(self, window):
        self.popup.destroy()
        self.popup = None

    def set_date(self, date):
        """sets date to specified, using default format"""
        self.date = date
        self.set_text(self._format_date(self.date))

    def get_date(self):
        """sets date to specified, using default format"""
        self.date = self._figure_date(self.get_text())
        self.set_text(self._format_date(self.date))
        return self.date

    def _figure_date(self, date_str):
        try:
            return dt.datetime.strptime(date_str, "%x").date()
        except:
            return self.date

    def _format_date(self, date):
        if not date:
            return ""
        else:
            return date.strftime("%x")

    def _on_text_changed(self, widget):
        self.news = True

    def __on_day_selected_double_click(self, calendar):
        self.prev_cal_day = None
        self._on_day_selected(calendar) #forward

    def _on_cal_button_press_event(self, calendar, event):
        self.prev_cal_day = calendar.get_date()[2]

    def _on_day_selected(self, calendar):
        if self.popup.get_property("visible") == False:
            return

        if self.prev_cal_day == calendar.get_date()[2]:
            return

        cal_date = calendar.get_date()

        self.date = dt.date(cal_date[0], cal_date[1] + 1, cal_date[2])
        self.set_text(self._format_date(self.date))

        self.hide_popup()
        if self.news:
            self.emit("date-entered")
            self.news = False

    def hide_popup(self):
        self.popup.hide()
        if self._parent_click_watcher and self.get_toplevel().handler_is_connected(self._parent_click_watcher):
            self.get_toplevel().disconnect(self._parent_click_watcher)
            self._parent_click_watcher = None

    def show_popup(self):
        if not self._parent_click_watcher:
            self._parent_click_watcher = self.get_toplevel().connect("button-press-event", self._on_focus_out_event)

        window = self.get_parent_window()
        x, y = window.get_origin()

        alloc = self.get_allocation()

        date = self._figure_date(self.get_text())
        if date:
            self.prev_cal_day = date.day #avoid
            self.date_calendar.select_month(date.month - 1, date.year)
            self.date_calendar.select_day(date.day)

        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)
        self.popup.show_all()

    def _on_focus_in_event(self, entry, event):
        self.show_popup()

    def _on_button_press_event(self, button, event):
        self.show_popup()


    def _on_focus_out_event(self, event, something):
        self.hide_popup()
        if self.news:
            self.emit("date-entered")
            self.news = False

    def _on_key_press_event(self, entry, event):
        if self.popup.get_property("visible"):
            cal_date = self.date_calendar.get_date()
            date = dt.date(cal_date[0], cal_date[1] + 1, cal_date[2])
        else:
            date = self._figure_date(entry.get_text())
            if not date:
                return

        enter_pressed = False

        if event.keyval == gtk.keysyms.Up:
            date = date - dt.timedelta(days=1)
        elif event.keyval == gtk.keysyms.Down:
            date = date + dt.timedelta(days=1)
        elif (event.keyval == gtk.keysyms.Return or
              event.keyval == gtk.keysyms.KP_Enter):
            enter_pressed = True
        elif (event.keyval == gtk.keysyms.Escape):
            self.hide_popup()
        elif event.keyval in (gtk.keysyms.Left, gtk.keysyms.Right):
            return False #keep calendar open and allow user to walk in text
        else:
            self.hide_popup()
            return False

        if enter_pressed:
            self.prev_cal_day = "borken"
        else:
            #prev_cal_day is our only way of checking that date is right
            self.prev_cal_day = date.day

        self.date_calendar.select_month(date.month - 1, date.year)
        self.date_calendar.select_day(date.day)
        return True
