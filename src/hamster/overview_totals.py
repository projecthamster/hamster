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
import locale

from gettext import ngettext

import os
import gtk, gobject
from collections import defaultdict

import widgets, reports
from configuration import runtime, dialogs, load_ui_file
from lib import stuff, charting
from lib.i18n import C_


class TotalsBox(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)
        self._gui = load_ui_file("overview_totals.ui")
        self.get_widget("reports_vbox").reparent(self) #mine!

        self.start_date, self.end_date = None, None

        #graphs
        x_offset = 0.4 # align all graphs to the left edge


        self.category_chart = charting.Chart(max_bar_width = 20,
                                             legend_width = x_offset,
                                             value_format = "%.1f")
        self.category_chart.connect("bar-clicked", self.on_category_clicked)
        self.selected_categories = []
        self.category_sums = None

        self.get_widget("totals_by_category").add(self.category_chart);

        self.activity_chart = charting.Chart(max_bar_width = 20,
                                             legend_width = x_offset,
                                             value_format = "%.1f")
        self.activity_chart.connect("bar-clicked", self.on_activity_clicked)
        self.selected_activities = []
        self.activity_sums = None

        self.get_widget("totals_by_activity").add(self.activity_chart);

        self.tag_chart = charting.Chart(max_bar_width = 20,
                                        legend_width = x_offset,
                                        value_format = "%.1f")
        self.tag_chart.connect("bar-clicked", self.on_tag_clicked)
        self.selected_tags = []
        self.tag_sums = None

        self.get_widget("totals_by_tag").add(self.tag_chart);

        self._gui.connect_signals(self)

        self.report_chooser = None


    def on_category_clicked(self, widget, key):
        if key in self.category_chart.selected_keys:
            self.category_chart.selected_keys.remove(key)
            self.selected_categories.remove(key)
        else:
            self.category_chart.selected_keys.append(key)
            self.selected_categories.append(key)

        self.calculate_totals()
        self.do_charts()

    def on_activity_clicked(self, widget, key):
        if key in self.activity_chart.selected_keys:
            self.activity_chart.selected_keys.remove(key)
            self.selected_activities.remove(key)
        else:
            self.activity_chart.selected_keys.append(key)
            self.selected_activities.append(key)
        self.calculate_totals()
        self.do_charts()

    def on_tag_clicked(self, widget, key):
        if key in self.tag_chart.selected_keys:
            self.tag_chart.selected_keys.remove(key)
            self.selected_tags.remove(key)
        else:
            self.tag_chart.selected_keys.append(key)
            self.selected_tags.append(key)
        self.calculate_totals()
        self.do_charts()


    def search(self, start_date, end_date, facts):
        self.facts = facts
        self.category_sums, self.activity_sums, self.tag_sums = [], [], []
        self.selected_categories, self.selected_activities, self.selected_tags = [], [], []
        self.category_chart.selected_keys, self.activity_chart.selected_keys, self.tag_chart.selected_keys = [], [], []

        self.start_date = start_date
        self.end_date = end_date

        self.do_graph()


    def do_graph(self):
        if self.facts:
            self.get_widget("no_data_label").hide()
            self.get_widget("charts").show()
            self.get_widget("total_hours").show()
            self.calculate_totals()
            self.do_charts()
        else:
            self.get_widget("no_data_label").show()
            self.get_widget("charts").hide()
            self.get_widget("total_hours").hide()


    def calculate_totals(self):
        if not self.facts:
            return
        facts = self.facts

        category_sums, activity_sums, tag_sums = defaultdict(dt.timedelta), defaultdict(dt.timedelta), defaultdict(dt.timedelta),

        for fact in facts:
            if self.selected_categories and fact.category not in self.selected_categories:
                continue
            if self.selected_activities and fact.activity not in self.selected_activities:
                continue
            if self.selected_tags and len(set(self.selected_tags) - set(fact.tags)) > 0:
                continue

            category_sums[fact.category] += fact.delta
            activity_sums[fact.activity] += fact.delta

            for tag in fact.tags:
                tag_sums[tag] += fact.delta

        total_label = _("%s hours tracked total") % locale.format("%.1f", stuff.duration_minutes([fact.delta for fact in facts]) / 60.0)
        self.get_widget("total_hours").set_text(total_label)


        for key in category_sums:
            category_sums[key] = stuff.duration_minutes(category_sums[key]) / 60.0

        for key in activity_sums:
            activity_sums[key] = stuff.duration_minutes(activity_sums[key]) / 60.0

        for key in tag_sums:
            tag_sums[key] = stuff.duration_minutes(tag_sums[key]) / 60.0


        #category totals
        if category_sums:
            if self.category_sums:
                category_sums = [(key, category_sums[key] or 0) for key in self.category_sums[0]]
            else:
                category_sums = sorted(category_sums.items(), key=lambda x:x[1], reverse = True)

            self.category_sums = zip(*category_sums)

        # activity totals
        if self.activity_sums:
            activity_sums = [(key, activity_sums[key] or 0) for key in self.activity_sums[0]]
        else:
            activity_sums = sorted(activity_sums.items(), key=lambda x:x[1], reverse = True)

        self.activity_sums = zip(*activity_sums)


        # tag totals
        if tag_sums:
            if self.tag_sums:
                tag_sums = [(key, tag_sums[key] or 0) for key in self.tag_sums[0]]
            else:
                tag_sums = sorted(tag_sums.items(), key=lambda x:x[1], reverse = True)
            self.tag_sums = zip(*tag_sums)


    def do_charts(self):
        self.get_widget("totals_by_category").set_size_request(10,10)
        if self.category_sums:
            self.get_widget("totals_by_category").set_size_request(-1, len(self.category_sums[0]) * 20)
            self.category_chart.plot(*self.category_sums)
        else:
            self.get_widget("totals_by_category").set_size_request(-1, 10)
            self.category_chart.plot([],[])

        if self.activity_sums:
            self.get_widget("totals_by_activity").set_size_request(10,10)
            self.get_widget("totals_by_activity").set_size_request(-1, len(self.activity_sums[0]) * 20)
            self.activity_chart.plot(*self.activity_sums)
        else:
            self.get_widget("totals_by_category").set_size_request(-1, 10)
            self.activity_chart.plot([],[])

        self.get_widget("totals_by_tag").set_size_request(10,10)
        if self.tag_sums:
            self.get_widget("totals_by_tag").set_size_request(-1, len(self.tag_sums[0]) * 20)
            self.tag_chart.plot(*self.tag_sums)
        else:
            self.get_widget("totals_by_tag").set_size_request(-1, 10)
            self.tag_chart.plot([],[])


    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def on_statistics_button_clicked(self, button):
        dialogs.stats.show(self)



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
