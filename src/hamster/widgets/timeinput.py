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

from ..lib.stuff import format_duration
import gtk
from gtk import keysyms
import datetime as dt
import calendar
import gobject
import re

class TimeInput(gtk.Entry):
    __gsignals__ = {
        'time-entered': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }


    def __init__(self, time = None, start_time = None):
        gtk.Entry.__init__(self)
        self.news = False
        self.set_width_chars(7) #7 is like 11:24pm

        self.set_time(time)
        self.set_start_time(start_time)

        self.popup = gtk.Window(type = gtk.WINDOW_POPUP)
        time_box = gtk.ScrolledWindow()
        time_box.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        time_box.set_shadow_type(gtk.SHADOW_IN)

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
        self._parent_click_watcher = None # bit lame but works

        self.connect("changed", self._on_text_changed)
        self.show()
        self.connect("destroy", self.on_destroy)

    def on_destroy(self, window):
        self.popup.destroy()
        self.popup = None

    def set_time(self, time):
        time = time or dt.time()
        if isinstance(time, dt.time): # ensure that we operate with time and strip seconds
            self.time = dt.time(time.hour, time.minute)
        else:
            self.time = dt.time(time.time().hour, time.time().minute)

        self.set_text(self._format_time(time))

    def set_start_time(self, start_time):
        """ set the start time. when start time is set, drop down list
            will start from start time and duration will be displayed in
            brackets
        """
        start_time = start_time or dt.time()
        if isinstance(start_time, dt.time): # ensure that we operate with time
            self.start_time = dt.time(start_time.hour, start_time.minute)
        else:
            self.start_time = dt.time(start_time.time().hour, start_time.time().minute)

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

        return dt.time(hours, minutes)


    def _select_time(self, time_text):
        #convert forth and back so we have text formated as we want
        time = self.figure_time(time_text)
        time_text = self._format_time(time)

        self.set_text(time_text)
        self.set_position(len(time_text))
        self.hide_popup()
        if self.news:
            self.emit("time-entered")
            self.news = False

    def get_time(self):
        self.time = self.figure_time(self.get_text())
        self.set_text(self._format_time(self.time))
        return self.time

    def _format_time(self, time):
        if time is None:
            return ""
        return time.strftime("%H:%M").lower()


    def _on_focus_in_event(self, entry, event):
        self.show_popup()

    def _on_button_press_event(self, button, event):
        self.show_popup()

    def _on_focus_out_event(self, event, something):
        self.hide_popup()
        if self.news:
            self.emit("time-entered")
            self.news = False

    def hide_popup(self):
        if self._parent_click_watcher and self.get_toplevel().handler_is_connected(self._parent_click_watcher):
            self.get_toplevel().disconnect(self._parent_click_watcher)
            self._parent_click_watcher = None
        self.popup.hide()

    def show_popup(self):
        if not self._parent_click_watcher:
            self._parent_click_watcher = self.get_toplevel().connect("button-press-event", self._on_focus_out_event)

        # will be going either 24 hours or from start time to start time + 12 hours
        start_time = dt.datetime.combine(dt.date.today(), self.start_time) # we will be adding things
        i_time = start_time # we will be adding things

        if self.start_time:
            end_time = i_time + dt.timedelta(hours = 12)
            i_time += dt.timedelta(minutes = 15)
        else:
            end_time = i_time + dt.timedelta(days = 1)


        focus_time = dt.datetime.combine(dt.date.today(), self.figure_time(self.get_text()))
        hours = gtk.ListStore(gobject.TYPE_STRING)


        i, focus_row = 0, None
        while i_time < end_time:
            row_text = self._format_time(i_time)
            if self.start_time:
                delta = (i_time - start_time).seconds / 60
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
            selection = self.time_tree.get_selection()
            selection.select_path(focus_row)
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
        if event.keyval not in (keysyms.Up, keysyms.Down, keysyms.Return, keysyms.KP_Enter):
            #any kind of other input
            self.hide_popup()
            return False

        model, iter = self.time_tree.get_selection().get_selected()
        if not iter:
            return


        i = model.get_path(iter)[0]
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
            self.hide_popup()
            return

        # keep it in sane limits
        i = min(max(i, 0), len(self.time_tree.get_model()) - 1)

        self.time_tree.set_cursor(i)
        self.time_tree.scroll_to_cell(i, use_align = True, row_align = 0.4)

        # if popup is not visible, display it on up and down
        if event.keyval in (gtk.keysyms.Up, gtk.keysyms.Down) and self.popup.props.visible == False:
            self.show_popup()

        return True
