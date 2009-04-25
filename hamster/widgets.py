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

class HamsterCalendar(gtk.Entry):
    """ a text entry widget with calendar popup"""
    __gsignals__ = {
        'date-entered': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }


    def __init__(self):
        gtk.Entry.__init__(self)
    
        self.prev_cal_day = None #workaround
        self.calendar_window = gtk.Window(type = gtk.WINDOW_POPUP)
        calendar_box = gtk.HBox()
        
        
        self.date_calendar = gtk.Calendar()
        
        self.date_calendar.connect("day-selected", self.on_day_selected)
        self.date_calendar.connect("day-selected-double-click", self.on_day_selected_double_click)
        self.date_calendar.connect("button-press-event", self.on_cal_button_press_event)
        calendar_box.add(self.date_calendar)
        self.calendar_window.add(calendar_box)

        self.connect("button-press-event", self.on_button_press_event)
        self.connect("key-press-event", self.on_key_press_event)
        self.connect("focus-in-event", self.on_focus_in_event)
        self.connect("focus-out-event", self.on_focus_out_event)
        self.show()

    def set_date(self, date):
        """sets date to specified, using default format"""
        self.set_text(self.format_date(date))

    def get_date(self):
        """sets date to specified, using default format"""
        return self.figure_date(self.get_text())

    def figure_date(self, date_str):
        try:
            return dt.datetime.strptime(date_str, "%x")
        except:
            return None

    def format_date(self, date):
        if not date:
            return ""
        else:
            return date.strftime("%x")

    def on_button_press_event(self, button, event):
        if self.calendar_window.get_property("visible"):
            self.calendar_window.hide()

    def on_day_selected_double_click(self, calendar):
        self.prev_cal_day = None
        self.on_day_selected(calendar) #forward
        
    def on_cal_button_press_event(self, calendar, event):
        self.prev_cal_day = calendar.get_date()[2]

    def on_day_selected(self, calendar):
        if self.calendar_window.get_property("visible") == False:
            return
        
        if self.prev_cal_day == calendar.get_date()[2]:
            return
        
        cal_date = calendar.get_date()

        date = dt.date(cal_date[0], cal_date[1] + 1, cal_date[2])
        
        self.set_text(self.format_date(date))

        self.calendar_window.hide()        
        self.emit("date-entered")
        
    
    def on_focus_in_event(self, entry, event):
        window = entry.get_parent_window()
        x, y= window.get_origin()

        alloc = entry.get_allocation()
        
        date = self.figure_date(entry.get_text())
        if date:
            self.prev_cal_day = date.day #avoid 
            self.date_calendar.select_month(date.month-1, date.year)
            self.date_calendar.select_day(date.day)
        
        self.calendar_window.move(x + alloc.x,y + alloc.y + alloc.height)
        self.calendar_window.show_all()

    def on_focus_out_event(self, event, something):
        self.calendar_window.hide()
        self.emit("date-entered")
    
    def on_key_press_event(self, entry, event):
        if self.calendar_window.get_property("visible"):
            cal_date = self.date_calendar.get_date()
            date = dt.date(cal_date[0], cal_date[1], cal_date[2])
        else:
            date = self.figure_date(entry.get_text())
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
            self.calendar_window.hide()
        elif event.keyval in (gtk.keysyms.Left, gtk.keysyms.Right):
            return False #keep calendar open and allow user to walk in text
        else:
            self.calendar_window.hide()
            return False
        
        if enter_pressed:
            self.prev_cal_day = "borken"
        else:
            self.prev_cal_day = date.day #prev_cal_day is our only way of checking that date is right
        
        self.date_calendar.select_month(date.month, date.year)
        self.date_calendar.select_day(date.day)
        return True
