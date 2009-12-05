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


import pygtk
pygtk.require('2.0')

import os
import gtk, gobject
import pango

import stuff

import widgets

from configuration import runtime, GconfStore

from stats_overview import OverviewBox
from stats_reports import ReportsBox
from stats_stats import StatsBox


class StatsViewer(object):
    def __init__(self, parent = None):
        self.parent = parent# determine if app should shut down on close
        self._gui = stuff.load_ui_file("stats.ui")

        self.window = self.get_widget("tabs_window")
        
        self.overview = OverviewBox()
        self.get_widget("overview_tab").add(self.overview)

        self.reports = ReportsBox()
        self.get_widget("reports_tab").add(self.reports)

        self.stats = StatsBox()
        self.get_widget("stats_tab").add(self.stats)

        self._gui.connect_signals(self)
        
        self.window.show_all()

        
    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def on_window_tabs_switch_page(self, notebook, page, pagenum):
        if pagenum == 2:
            year = None
            for child in self.stats.get_widget("year_box").get_children():
                if child.get_active():
                    year = child.year
            
            self.stats.stats(year)
        elif pagenum == 1:
            self.reports.do_graph()

    def on_close(self, widget, event):
        runtime.dispatcher.del_handler('activity_updated',
                                       self.after_activity_update)
        runtime.dispatcher.del_handler('day_updated', self.after_fact_update)
        self.close_window()        

    def on_window_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w 
              and event_key.state & gtk.gdk.CONTROL_MASK)):
        self.close_window()
    
    
    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            return False
        
    def show(self):
        self.window.show()

