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

from configuration import runtime, GconfStore

from stats_overview import OverviewBox
from stats_reports import ReportsBox
from stats_stats import StatsBox

import widgets
import charting
import datetime as dt
import calendar

from hamster.i18n import C_


class StatsViewer(object):
    def __init__(self, parent = None):
        self.parent = parent# determine if app should shut down on close
        self._gui = stuff.load_ui_file("stats.ui")

        self.window = self.get_widget("tabs_window")


        self.view_date = dt.date.today()
        #set to monday
        self.start_date = self.view_date - \
                                      dt.timedelta(self.view_date.weekday() + 1)
        # look if we need to start on sunday or monday
        self.start_date = self.start_date + \
                                      dt.timedelta(stuff.locale_first_weekday())
        
        self.end_date = self.start_date + dt.timedelta(6)

        
        self.overview = OverviewBox()
        self.get_widget("overview_tab").add(self.overview)

        self.reports = ReportsBox()
        self.get_widget("reports_tab").add(self.reports)
        
        self.range_combo = gtk.combo_box_new_text()
        self.range_combo.append_text(_("Week"))
        self.range_combo.append_text(_("Month"))
        self.range_combo.append_text(_("Date Range"))
        self.range_combo.set_row_separator_func(lambda row, iter: row[iter][0] == "-")
        self.range_combo.append_text("-")
        self.range_combo.append_text("All")
        self.range_combo.set_active(0)
        self.range_combo.connect("changed", self.on_range_combo_changed)
        
        
        
        self.get_widget("range_pick").add(self.range_combo)


        self.start_date_input = widgets.DateInput(self.start_date)
        self.start_date_input.connect("date-entered", self.on_start_date_entered)
        self.get_widget("range_start_box").add(self.start_date_input)

        self.end_date_input = widgets.DateInput(self.end_date)
        self.end_date_input.connect("date-entered", self.on_end_date_entered)
        self.get_widget("range_end_box").add(self.end_date_input)

        self._gui.connect_signals(self)
        self.window.show_all()


        self.search()

    def set_title(self):
        dates_dict = stuff.dateDict(self.start_date, "start_")
        dates_dict.update(stuff.dateDict(self.end_date, "end_"))
        
        if self.start_date.year != self.end_date.year:
            # overview label if start and end years don't match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            overview_label = _(u"%(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif self.start_date.month != self.end_date.month:
            # overview label if start and end month do not match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            overview_label = _(u"%(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        else:
            # overview label for interval in same month
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            overview_label = _(u"%(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict

        
        self.get_widget("overview_label").set_markup("<b>%s</b>" % overview_label)


    def search(self):
        self.set_title()
        self.start_date_input.set_date(self.start_date)
        self.end_date_input.set_date(self.end_date)
        
        facts = runtime.storage.get_facts(self.start_date, self.end_date)
        self.get_widget("report_button").set_sensitive(len(facts) > 0)
        
        self.overview.search(self.start_date, self.end_date, facts)
        self.reports.search(self.start_date, self.end_date, facts)
        
        
    def on_report_button_clicked(self, widget):
        self.reports.on_report_button_clicked(widget) #forward for now


    def on_range_combo_changed(self, combo):
        idx = combo.get_active()

        self.get_widget("preset_range").hide()
        self.get_widget("range_box").hide()
        
        if idx == 0: # week
            self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
            self.start_date = self.start_date + dt.timedelta(stuff.locale_first_weekday())
            self.end_date = self.start_date + dt.timedelta(6)
            self.get_widget("preset_range").show()

        elif idx == 1: #month
            self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
            first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
            self.get_widget("preset_range").show()

        elif idx == 2:
            self.get_widget("range_box").show()
            
        self.search()
        
    def on_start_date_entered(self, input):
        self.start_date = input.get_date().date()
        self.view_date = self.start_date
        self.search()

    def on_end_date_entered(self, input):
        self.end_date = input.get_date().date()
        self.search()

    def _chosen_range(self):
        return self.range_combo.get_active() 

    def on_prev_clicked(self, button):
        if self._chosen_range() == 0:  # week
            self.start_date -= dt.timedelta(7)
            self.end_date -= dt.timedelta(7)        
        elif self._chosen_range() == 1: # month
            self.end_date = self.start_date - dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.end_date.year, self.end_date.month)
            self.start_date = self.end_date - dt.timedelta(days_in_month - 1)

        self.view_date = self.start_date
        self.search()

    def on_next_clicked(self, button):
        if self._chosen_range() == 0:  # week
            self.start_date += dt.timedelta(7)
            self.end_date += dt.timedelta(7)        
        elif self._chosen_range() == 1: # month
            self.start_date = self.end_date + dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.start_date.year, self.start_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
    
        self.view_date = self.start_date
        self.search()


    def on_home_clicked(self, button):
        self.view_date = dt.date.today()
        if self._chosen_range() == 0: # week
            self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
            self.start_date = self.start_date + dt.timedelta(stuff.locale_first_weekday())
            self.end_date = self.start_date + dt.timedelta(6)
        
        elif self._chosen_range() == 1: # month
            self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
            first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
        
        self.search()
        
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

