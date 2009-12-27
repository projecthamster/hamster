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

import datetime as dt
import calendar
import time
import webbrowser
from itertools import groupby

import pygtk
pygtk.require('2.0')

from gettext import ngettext

import os
import gtk, gobject

import stuff, widgets
import charting, reports
from configuration import runtime, GconfStore

from hamster.i18n import C_


class ReportsBox(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)
        self._gui = stuff.load_ui_file("stats_reports.ui")
        self.get_widget("reports_vbox").reparent(self) #mine!

        self.start_date, self.end_date = None, None

        #graphs
        self.background = (0.975, 0.975, 0.975)
        self.get_widget("reports_box").modify_bg(gtk.STATE_NORMAL,
                      gtk.gdk.Color(*[int(b*65536.0) for b in self.background]))

        x_offset = 100 # align all graphs to the left edge


        self.category_chart = charting.HorizontalBarChart(background = self.background,
                                                          max_bar_width = 20,
                                                          legend_width = x_offset,
                                                          value_format = "%.1f",
                                                          animate = False)
        self.get_widget("totals_by_category").add(self.category_chart);
        
        self.activity_chart = charting.HorizontalBarChart(background = self.background,
                                                          max_bar_width = 20,
                                                          legend_width = x_offset,
                                                          value_format = "%.1f",
                                                          animate = False)
        self.get_widget("totals_by_activity").add(self.activity_chart);

        self.tag_chart = charting.HorizontalBarChart(background = self.background,
                                                          max_bar_width = 20,
                                                          legend_width = x_offset,
                                                          value_format = "%.1f",
                                                          animate = False)
        self.get_widget("totals_by_tag").add(self.tag_chart);


        self._gui.connect_signals(self)
        
        self.config = GconfStore()
        runtime.dispatcher.add_handler('gconf_on_day_start_changed', self.on_day_start_changed)

        self.report_chooser = None

    def on_reports_box_expose_event(self, box, someth):
        self.do_charts()

    def search(self, start_date, end_date, facts):
        self.facts = facts
        self.start_date = start_date
        self.end_date = end_date
        self.do_graph()

    def do_graph(self):
        if self.facts:
            self.get_widget("no_data_label").hide()
            self.get_widget("charts").show()
            self.do_charts()
        else:
            self.get_widget("no_data_label").show()
            self.get_widget("charts").hide()


    def do_charts(self):
        if not self.facts:
            return
        
        #totals by category
        category_sums = stuff.totals(self.facts,
                                     lambda fact: (fact["category"]),
                                     lambda fact: stuff.duration_minutes(fact["delta"]) / 60.0)
        if category_sums:
            category_sums = sorted(category_sums.items(), key=lambda x:x[1], reverse = True)
            keys, values = zip(*category_sums)
            self.get_widget("totals_by_category").set_size_request(280, len(keys) * 20)
            self.category_chart.plot(keys, values)
        else:
            self.category_chart.plot([], [])
        

        #totals by activity
        activity_sums = stuff.totals(self.facts,
                                     lambda fact: (fact["name"]),
                                     lambda fact: stuff.duration_minutes(fact["delta"]) / 60.0)
        activity_sums = sorted(activity_sums.items(), key=lambda x:x[1], reverse = True)
        keys, values = zip(*activity_sums)
        self.get_widget("totals_by_activity").set_size_request(10,10)
        self.get_widget("totals_by_activity").set_size_request(280, len(keys) * 20)
        self.activity_chart.plot(keys, values)


        tag_sums = {}
        for fact in self.facts:
            for tag in fact["tags"]:
                tag_sums.setdefault(tag, 0)
                tag_sums[tag] += stuff.duration_minutes(fact["delta"]) / 60.0

        if tag_sums:        
            tag_sums = sorted(tag_sums.items(), key=lambda x:x[1], reverse = True)
            keys, values = zip(*tag_sums)
            self.get_widget("totals_by_tag").set_size_request(10,10)
            self.get_widget("totals_by_tag").set_size_request(280, len(keys) * 20)
            self.tag_chart.plot(keys, values)
        else:
            self.tag_chart.plot([], [])
        

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def on_day_start_changed(self, event, new_minutes):
        self.do_graph()



if __name__ == "__main__":
    gtk.window_set_default_icon_name("hamster-applet")    
    window = gtk.Window()
    window.set_title("Hamster - reports")
    window.set_size_request(800, 600)
    reports = ReportsBox()
    window.add(reports)
    window.connect("delete_event", lambda *args: gtk.main_quit())
    window.show_all()

    start_date = dt.date.today() - dt.timedelta(days=30)    
    end_date = dt.date.today()
    facts = runtime.storage.get_facts(start_date, end_date)
    reports.search(start_date, end_date, facts)
    

    gtk.main()    

