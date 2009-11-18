#!/usr/bin/env python
# - coding: utf-8 -

# Copyright (C) 2009 Toms Bauģis <toms.baugis at gmail.com>

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

import logging
import datetime as dt

import pygtk
pygtk.require("2.0")
import gtk
#gtk.gdk.threads_init()

from configuration import GconfStore, runtime
import stuff, widgets

class MainWindow(object):
    def __init__(self):
        self._gui = stuff.load_ui_file("hamster.ui")
        self.window = self._gui.get_object('main-window')

        self.style_widgets()
        
        self.get_widget("tabs").set_current_page(1)

        self.set_last_activity()
        self._gui.connect_signals(self)

    def style_widgets(self):
        #TODO - replace with the tree background color (can't get it atm!)
        self.get_widget("todays_activities_ebox").modify_bg(gtk.STATE_NORMAL,
                                                                 gtk.gdk.Color(65536.0,65536.0,65536.0))
        
        self.new_name = widgets.HintEntry(_("Time and Name"), self.get_widget("new_name"))
        self.new_description = widgets.HintEntry(_("Tags or Description"), self.get_widget("new_description"))
        

    def set_last_activity(self):
        activity = runtime.storage.get_last_activity()
        if activity:
            delta = dt.datetime.now() - activity['start_time']
            duration = delta.seconds /  60
            
            self.get_widget("last_activity_duration").set_text(stuff.format_duration(duration))
            self.get_widget("last_activity_name").set_text(activity['name'])
            if activity['category'] != _("Unsorted"):
                self.get_widget("last_activity_category") \
                    .set_markup("<small>%s</small>" %
                                       stuff.escape_pango(activity['category']))
                self.get_widget("last_activity_category").show()
            else:
                self.get_widget("last_activity_category").show()

            if activity['description']:
                self.get_widget("last_activity_description").set_text(activity['description'])
                self.get_widget("last_activity_description").show()
            else:
                self.get_widget("last_activity_description").hide()

    def on_switch_activity_clicked(self, widget):
        self.get_widget("new_entry_box").show()

    def show(self):
        self.window.show_all()
        
    def get_widget(self, name):
        return self._gui.get_object(name)
        
    

if __name__ == "__main__":
    gtk.window_set_default_icon_name("hamster-applet")
    MainWindow().show()
    
    gtk.main()    

