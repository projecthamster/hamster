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

import calendar
import re

from gi.repository import Gdk as gdk
from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject

from hamster.lib import datetime as dt
from hamster.lib.stuff import hamster_round

class TimeInput(gtk.Entry):
    __gsignals__ = {
        'time-entered': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }


    def __init__(self, time=None, start_time=None, *, parent, **kwargs):
        gtk.Entry.__init__(self, parent=parent, **kwargs)
        self.news = False
        self.set_width_chars(7) #7 is like 11:24pm

        self.time = time
        self.set_start_time(start_time)


        self.popup = gtk.Window(type = gtk.WindowType.POPUP)
        self.popup.set_type_hint(gdk.WindowTypeHint.COMBO)  # why not
        self.popup.set_attached_to(self)  # attributes
        self.popup.set_transient_for(self.get_ancestor(gtk.Window))  # position

        time_box = gtk.ScrolledWindow()
        time_box.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.ALWAYS)
        time_box.set_shadow_type(gtk.ShadowType.IN)

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

        self.set_icon_from_icon_name(gtk.EntryIconPosition.PRIMARY, "edit-clear-all-symbolic")

        self.connect("icon-release", self._on_icon_release)
        self.connect("button-press-event", self._on_button_press_event)
        self.connect("key-press-event", self._on_key_press_event)
        self.connect("focus-in-event", self._on_focus_in_event)
        self.connect("focus-out-event", self._on_focus_out_event)
        self._parent_click_watcher = None # bit lame but works

        self.connect("changed", self._on_text_changed)
        self.show()
        self.connect("destroy", self.on_destroy)

    @property
    def time(self):
        """Displayed time.

         None,
         or time type,
         or datetime if start_time() was given a datetime.
         """
        time = self.figure_time(self.get_text())
        if self.start_date and time:
            # recombine (since self.start_time contains only the time part)
            start = dt.datetime.combine(self.start_date, self.start_time)
            new = dt.datetime.combine(self.start_date, time)
            if new < start:
                # a bit hackish, valid only because
                # duration can not be negative if start_time was given,
                # and we accept that it can not exceed 24h.
                # For longer durations,
                # date will have to be changed subsequently.
                return new + dt.timedelta(days=1)
            else:
                return new
        else:
            return time

    @time.setter
    def time(self, value):
        time = hamster_round(value)
        self.set_text(self._format_time(time))
        return time

    def on_destroy(self, window):
        self.popup.destroy()
        self.popup = None

    def set_start_time(self, start_time):
        """ Set the start time.

        When start time is set, drop down list will start from start time,
        and duration will be displayed in brackets.

        self.time will have the same type as start_time.
        """
        start_time = hamster_round(start_time)
        if isinstance(start_time, dt.datetime):
            self.start_date = start_time.date()
            # timeinput works on time only
            start_time = start_time.time()
        else:
            self.start_date = None
        self.start_time = start_time

    def _on_text_changed(self, widget):
        self.news = True

    def figure_time(self, str_time):
        if not str_time:
            return None

        # strip everything non-numeric and consider hours to be first number
        # and minutes - second number
        numbers = re.split("\D", str_time)
        numbers = [x for x in numbers if x!=""]

        hours, minutes = None, None

        if len(numbers) == 1 and len(numbers[0]) == 4:
            hours, minutes = int(numbers[0][:2]), int(numbers[0][2:])
        else:
            if len(numbers) >= 1:
                hours = int(numbers[0])
            if len(numbers) >= 2:
                minutes = int(numbers[1])

        if (hours is None or minutes is None) or hours > 24 or minutes > 60:
            return None  # no can do

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

    def _on_icon_release(self, entry, icon_pos, event):
        self.grab_focus()
        self.set_text("")
        self.emit("changed")

    def hide_popup(self):
        if self._parent_click_watcher and self.get_toplevel().handler_is_connected(self._parent_click_watcher):
            self.get_toplevel().disconnect(self._parent_click_watcher)
            self._parent_click_watcher = None
        self.popup.hide()

    def show_popup(self):
        if not self._parent_click_watcher:
            self._parent_click_watcher = self.get_toplevel().connect("button-press-event", self._on_focus_out_event)

        # we will be adding things, need datetime
        i_time_0 = dt.datetime.combine(self.start_date or dt.date.today(),
                                       self.start_time or dt.time())

        if self.start_time is None:
            # full 24 hours
            i_time = i_time_0
            interval = dt.timedelta(minutes = 15)
            end_time = i_time_0 + dt.timedelta(days = 1)
        else:
            # from start time to start time + 12 hours
            interval = dt.timedelta(minutes = 15)
            i_time = i_time_0 + interval
            end_time = i_time_0 + dt.timedelta(hours = 12)

        time = self.figure_time(self.get_text())
        focus_time = dt.datetime.combine(dt.date.today(), time) if time else None
        hours = gtk.ListStore(str)

        i, focus_row = 0, None
        while i_time < end_time:
            row_text = self._format_time(i_time)
            if self.start_time is not None:
                delta_text = (i_time - i_time_0).format()

                row_text += " (%s)" % delta_text

            hours.append([row_text])

            if focus_time and i_time <= focus_time < i_time + interval:
                focus_row = i

            i_time += interval

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
        self.time_tree.set_size_request(w, alloc.height * 5)

        window = self.get_parent_window()
        dmmy, x, y= window.get_origin()

        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)
        self.popup.resize(*self.time_tree.get_size_request())
        self.popup.show_all()

    def toggle_popup(self):
        if self.popup.get_property("visible"):
            self.hide_popup()
        else:
            self.show_popup()

    def _on_time_tree_button_press_event(self, tree, event):
        model, iter = tree.get_selection().get_selected()
        time = model.get_value(iter, 0)
        self._select_time(time)


    def _on_key_press_event(self, entry, event):
        if event.keyval not in (gdk.KEY_Up, gdk.KEY_Down, gdk.KEY_Return, gdk.KEY_KP_Enter):
            #any kind of other input
            self.hide_popup()
            return False

        model, iter = self.time_tree.get_selection().get_selected()
        if not iter:
            return


        i = model.get_path(iter)[0]
        if event.keyval == gdk.KEY_Up:
            i-=1
        elif event.keyval == gdk.KEY_Down:
            i+=1
        elif (event.keyval == gdk.KEY_Return or
              event.keyval == gdk.KEY_KP_Enter):

            if self.popup.get_property("visible"):
                self._select_time(self.time_tree.get_model()[i][0])
            else:
                self._select_time(entry.get_text())
        elif (event.keyval == gdk.KEY_Escape):
            self.hide_popup()
            return

        # keep it in sane limits
        i = min(max(i, 0), len(self.time_tree.get_model()) - 1)

        self.time_tree.set_cursor(i)
        self.time_tree.scroll_to_cell(i, use_align = True, row_align = 0.4)

        # if popup is not visible, display it on up and down
        if event.keyval in (gdk.KEY_Up, gdk.KEY_Down) and self.popup.props.visible == False:
            self.show_popup()

        return True
