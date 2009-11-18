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

from stuff import format_duration
import gtk
import datetime as dt
import calendar
import gobject
import re

import pango


class HintEntry(gtk.Entry):
    """a gtk.Entry that displays greyed out hint in the box, while not focused"""
    def __init__(self, hint, original_entry = None):
        gtk.Entry.__init__(self)

        self.hint = hint        
        self._set_hint()
        
        self.connect('focus-in-event', self.on_focus_in)
        self.connect('focus-out-event', self.on_focus_out)

        if original_entry:        
            parent = original_entry.parent
            parent.remove(original_entry)
    
            if original_entry.name:
                self.set_name(original_entry.name)
                
            parent.add(self)


        self.show()

    def _set_hint(self):
        if self.get_text(): # don't mess with user entered text
            return 

        self.modify_text(gtk.STATE_NORMAL, gtk.gdk.Color("gray"))
        hint_font = pango.FontDescription(gtk.Style().font_desc.to_string())
        hint_font.set_style(pango.STYLE_ITALIC)
        self.modify_font(hint_font)
        
        self.set_text(self.hint)
        
    def _set_normal(self):
        self.modify_text(gtk.STATE_NORMAL, gtk.Style().fg[gtk.STATE_NORMAL])
        hint_font = pango.FontDescription(gtk.Style().font_desc.to_string())
        self.modify_font(hint_font)

        if self.get_text() == self.hint:
            self.set_text("")

    def on_focus_in(self, widget, event):
        self._set_normal()

    def on_focus_out(self, widget, event):
        self._set_hint()



class DateInput(gtk.Entry):
    """ a text entry widget with calendar popup"""
    __gsignals__ = {
        'date-entered': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }


    def __init__(self, date = None):
        gtk.Entry.__init__(self)
        
        self.set_width_chars(12) #12 is enough for 12-oct-2009, which is verbose
        self.date = date
        if date:
            self.set_date(date)

        self.news = False
        self.prev_cal_day = None #workaround
        self.popup = gtk.Window(type = gtk.WINDOW_POPUP)
        calendar_box = gtk.HBox()

        self.date_calendar = gtk.Calendar()
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
        self.connect("changed", self._on_text_changed)
        self.show()

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
            return dt.datetime.strptime(date_str, "%x")
        except:
            return self.date

    def _format_date(self, date):
        if not date:
            return ""
        else:
            return date.strftime("%x")

    def _on_text_changed(self, widget):
        self.news = True
        
    def _on_button_press_event(self, button, event):
        self.popup.show()

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

        self.popup.hide()
        if self.news:
            self.emit("date-entered")
            self.news = False
        
    
    def _on_focus_in_event(self, entry, event):
        window = entry.get_parent_window()
        x, y= window.get_origin()

        alloc = entry.get_allocation()
        
        date = self._figure_date(entry.get_text())
        if date:
            self.prev_cal_day = date.day #avoid 
            self.date_calendar.select_month(date.month-1, date.year)
            self.date_calendar.select_day(date.day)
        
        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)
        self.popup.show_all()

    def _on_focus_out_event(self, event, something):
        self.popup.hide()
        if self.news:
            self.emit("date-entered")
            self.news = False
    
    def _on_key_press_event(self, entry, event):
        if self.popup.get_property("visible"):
            cal_date = self.date_calendar.get_date()
            date = dt.date(cal_date[0], cal_date[1], cal_date[2])
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
            self.popup.hide()
        elif event.keyval in (gtk.keysyms.Left, gtk.keysyms.Right):
            return False #keep calendar open and allow user to walk in text
        else:
            self.popup.hide()
            return False
        
        if enter_pressed:
            self.prev_cal_day = "borken"
        else:
            #prev_cal_day is our only way of checking that date is right
            self.prev_cal_day = date.day 
        
        self.date_calendar.select_month(date.month, date.year)
        self.date_calendar.select_day(date.day)
        return True


class TimeInput(gtk.Entry):
    __gsignals__ = {
        'time-entered': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }


    def __init__(self, time = None, start_time = None):
        gtk.Entry.__init__(self)

        self.start_time = start_time
        self.news = False

        self.set_width_chars(7) #7 is like 11:24pm
        self.time = time
        if time:
            self.set_time(time)


        self.popup = gtk.Window(type = gtk.WINDOW_POPUP)
        time_box = gtk.ScrolledWindow()
        time_box.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)

        self.time_tree = gtk.TreeView()
        self.time_tree.set_headers_visible(False)
        self.time_tree.set_hover_selection(True)

        self.time_tree.append_column(gtk.TreeViewColumn("Time",
                                                        gtk.CellRendererText(),
                                                        text=0))
        self.time_tree.connect("button-press-event",
                               self._on_time_tree_button_press_event)

        time_box.add(self.time_tree)
        self.popup.add(time_box)

        self.connect("button-press-event", self._on_button_press_event)
        self.connect("key-press-event", self._on_key_press_event)
        self.connect("focus-in-event", self._on_focus_in_event)
        self.connect("focus-out-event", self._on_focus_out_event)
        self.connect("changed", self._on_text_changed)
        self.show()


    def set_start_time(self, start_time):
        """ set the start time. when start time is set, drop down list
            will start from start time and duration will be displayed in
            brackets
        """
        self.start_time = start_time

    def set_time(self, time):
        self.time = time
        self.set_text(self._format_time(time))
        
    def _on_text_changed(self, widget):
        self.news = True
        
    def figure_time(self, str_time):
        if not str_time:
            return self.time
        
        # strip everything non-numeric and consider hours to be first number
        # and minutes - second number
        numbers = re.split("\D", str_time)
        numbers = filter(lambda x: x!="", numbers)
        
        hours, minutes = None, None
        
        if len(numbers) == 1 and len(numbers[0]) == 4:
            hours, minutes = int(numbers[0][:2]), int(numbers[0][2:])
        else:
            if len(numbers) >= 1:
                hours = int(numbers[0])
            if len(numbers) >= 2:
                minutes = int(numbers[1])
            
        if (hours is None or minutes is None) or hours > 24 or minutes > 60:
            return self.time #no can do
    
        return dt.datetime.now().replace(hour = hours, minute = minutes,
                                         second = 0, microsecond = 0)


    def _select_time(self, time_text):
        #convert forth and back so we have text formated as we want
        time = self.figure_time(time_text)
        time_text = self._format_time(time) 
        
        self.set_text(time_text)
        self.set_position(len(time_text))
        self.popup.hide()
        if self.news:
            self.emit("time-entered")
            self.news = False
    
    def get_time(self):
        self.time = self.figure_time(self.get_text())
        self.set_text(self._format_time(self.time))
        return self.time

    def _format_time(self, time):
        if time is None:
            return None
        
        #return time.strftime("%I:%M%p").lstrip("0").lower()
        return time.strftime("%H:%M").lower()
    

    def _on_focus_in_event(self, entry, event):
        self.show_popup()

    def _on_focus_out_event(self, event, something):
        self.popup.hide()
        if self.news:
            self.emit("time-entered")
            self.news = False
        

    def show_popup(self):
        focus_time = self.figure_time(self.get_text())
        
        hours = gtk.ListStore(gobject.TYPE_STRING)
        
        # populate times
        i_time = self.start_time or dt.datetime(1900, 1, 1, 0, 0)
        
        if focus_time and focus_time < i_time:
            focus_time += dt.timedelta(days = 1)
        
        if self.start_time:
            end_time = i_time + dt.timedelta(hours = 12)
            i_time += dt.timedelta(minutes = 15)
        else:
            end_time = i_time + dt.timedelta(hours = 24)
        
        i, focus_row = 0, None
        
        while i_time < end_time:
            row_text = self._format_time(i_time)
            if self.start_time:
                delta = (i_time - self.start_time).seconds / 60
                delta_text = format_duration(delta)
                
                row_text += " (%s)" % delta_text

            hours.append([row_text])
            
            if focus_time and i_time <= focus_time <= i_time + \
                                                     dt.timedelta(minutes = 30):
                focus_row = i
            
            if self.start_time:
                i_time += dt.timedelta(minutes = 15)
            else:
                i_time += dt.timedelta(minutes = 30)

            i += 1

        self.time_tree.set_model(hours)        

        #focus on row
        if focus_row != None:
            self.time_tree.set_cursor(focus_row)
            self.time_tree.scroll_to_cell(focus_row, use_align = True, row_align = 0.4)
        
        #move popup under the widget
        alloc = self.get_allocation()
        w = alloc.width
        if self.start_time:
            w = w * 2
        self.time_tree.set_size_request(w, alloc.height * 5)

        window = self.get_parent_window()
        x, y= window.get_origin()

        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)
        self.popup.show_all()

    
    def _on_time_tree_button_press_event(self, tree, event):
        model, iter = tree.get_selection().get_selected()
        time = model.get_value(iter, 0)
        self._select_time(time)
        
        
    def _on_key_press_event(self, entry, event):
        cursor = self.time_tree.get_cursor()

        if not cursor or not cursor[0]:
            return
        
        i = cursor[0][0]

        if event.keyval == gtk.keysyms.Up:
            i-=1
        elif event.keyval == gtk.keysyms.Down:
            i+=1
        elif (event.keyval == gtk.keysyms.Return or
              event.keyval == gtk.keysyms.KP_Enter):
            
            if self.popup.get_property("visible"):
                self._select_time(self.time_tree.get_model()[i][0])
            else:
                self._select_time(entry.get_text())
        elif (event.keyval == gtk.keysyms.Escape):
            self.popup.hide()
        else:
            #any kind of other input
            self.popup.hide()
            return False
        
        # keep it in the sane borders
        i = min(max(i, 0), len(self.time_tree.get_model()) - 1)
        
        self.time_tree.set_cursor(i)
        self.time_tree.scroll_to_cell(i, use_align = True, row_align = 0.4)
        return True
        
        
    def _on_button_press_event(self, button, event):
        self.popup.show()


    
