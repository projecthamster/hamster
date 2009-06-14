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

from hamster import dispatcher, storage, SHARED_DATA_DIR, stuff
from hamster import charting

from hamster.edit_activity import CustomFactController
from hamster import reports, widgets, graphics
import webbrowser

from itertools import groupby

import datetime as dt
import calendar
import time

class ReportChooserDialog(gtk.Dialog):
    __gsignals__ = {
        # format, path, start_date, end_date
        'report-chosen': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, gobject.TYPE_STRING,
                           gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,
                           gobject.TYPE_PYOBJECT)),
        'report-chooser-closed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }
    def __init__(self):
        gtk.Dialog.__init__(self)
        ui = stuff.load_ui_file("stats.ui")
        self.dialog = ui.get_object('save_report_dialog')

        self.dialog.set_action(gtk.FILE_CHOOSER_ACTION_SAVE)
        self.dialog.set_current_folder(os.path.expanduser("~"))

        self.filters = {}

        filter = gtk.FileFilter()
        filter.set_name(_("HTML Report"))
        filter.add_mime_type("text/html")
        filter.add_pattern("*.html")
        filter.add_pattern("*.htm")
        self.filters[filter] = "html"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("Tab Separated Values (TSV)"))
        filter.add_mime_type("text/plain")
        filter.add_pattern("*.tsv")
        filter.add_pattern("*.txt")
        self.filters[filter] = "tsv"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("XML"))
        filter.add_mime_type("text/xml")
        filter.add_pattern("*.xml")
        self.filters[filter] = "xml"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("iCal"))
        filter.add_mime_type("text/calendar")
        filter.add_pattern("*.ics")
        self.filters[filter] = "ical"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        self.dialog.add_filter(filter)
        
        self.start_date = widgets.DateInput()
        ui.get_object('from_date_box').add(self.start_date)
        self.end_date = widgets.DateInput()
        ui.get_object('to_date_box').add(self.end_date)

        self.category_box = ui.get_object('category_box')

        ui.get_object('save_button').connect("clicked", self.on_save_button_clicked)
        ui.get_object('cancel_button').connect("clicked", self.on_cancel_button_clicked)
        

    def show(self, start_date, end_date):
        #set suggested name to something readable, replace backslashes with dots
        #so the name is valid in linux
        filename = "Time track %s - %s" % (start_date.strftime("%x").replace("/", "."),
                                           end_date.strftime("%x").replace("/", "."))
        self.dialog.set_current_name(filename)
        
        self.start_date.set_date(start_date)
        self.end_date.set_date(end_date)
        
        #add unsorted category
        button_all = gtk.RadioButton(None, _("All").encode("utf-8"))
        button_all.value = None
        button_all.set_active(True)
        self.category_box.pack_start(button_all)

        categories = storage.get_category_list()
        for category in categories:
            button = gtk.RadioButton(button_all, category['name'].encode("utf-8"))
            button.value = category['id']
            self.category_box.pack_start(button)
        

        response = self.dialog.show_all()

    def present(self):
        self.dialog.present()

    def on_save_button_clicked(self, widget):
        path, format = None,  None

        format = "html"
        if self.dialog.get_filter() in self.filters:
            format = self.filters[self.dialog.get_filter()]
        path = self.dialog.get_filename()
        
        category = None
        for button in self.category_box.get_children():
            if button.get_active():
                category = button.value
        
        # format, path, start_date, end_date
        self.emit("report-chosen", format, path,
                           self.start_date.get_date().date(),
                           self.end_date.get_date().date(),
                           category)
        self.dialog.destroy()
        

    def on_cancel_button_clicked(self, widget):
        self.emit("report-chooser-closed")
        self.dialog.destroy()

class StatsViewer(object):
    def __init__(self, parent = None):
        self.parent = parent# determine if app shut shut down on close
        self._gui = stuff.load_ui_file("stats.ui")
        self.window = self.get_widget('stats_window')
        self.stat_facts = None

        #id, caption, duration, date (invisible), description, category
        self.fact_store = gtk.TreeStore(int, str, str, str, str, str) 
        self.setup_tree()
        
        self.background = (0.975,0.975,0.975)
        self.get_widget("graph_frame").modify_bg(gtk.STATE_NORMAL,
                      gtk.gdk.Color(*[int(b*65536.0) for b in self.background]))

        
        x_offset = 90 # let's nicely align all graphs
        
        self.category_chart = charting.BarChart(background = self.background,
                                             bar_base_color = (238,221,221),
                                             bars_beveled = False,
                                             legend_width = x_offset,
                                             max_bar_width = 35,
                                             show_stack_labels = True
                                             )
        category_box = self.get_widget("totals_by_category")
        category_box.add(self.category_chart)
        category_box.set_size_request(130, -1)
        

        self.day_chart = charting.BarChart(background = self.background,
                                        bar_base_color = (220, 220, 220),
                                        bars_beveled = False,
                                        show_scale = True,
                                        max_bar_width = 35,
                                        grid_stride = 4,
                                        legend_width = 20)
        self.get_widget("totals_by_day").add(self.day_chart)


        self.activity_chart = charting.HorizontalBarChart(orient = "horizontal",
                                             max_bar_width = 25,
                                             values_on_bars = True,
                                             stretch_grid = True,
                                             legend_width = x_offset,
                                             value_format = "%.1f",
                                             background = self.background,
                                             bars_beveled = False,
                                             animate = False)
        self.get_widget("totals_by_activity").add(self.activity_chart);

        
        self.view_date = dt.date.today()
        
         #set to monday
        self.start_date = self.view_date - \
                                      dt.timedelta(self.view_date.weekday() + 1)
        # look if we need to start on sunday or monday
        self.start_date = self.start_date + \
                                      dt.timedelta(self.locale_first_weekday())
        
        self.end_date = self.start_date + dt.timedelta(6)

        
        self.week_view = self.get_widget("week")
        self.month_view = self.get_widget("month")
        self.month_view.set_group(self.week_view)
        
        #initiate the form in the week view
        self.week_view.set_active(True)


        dispatcher.add_handler('activity_updated', self.after_activity_update)
        dispatcher.add_handler('day_updated', self.after_fact_update)

        selection = self.fact_tree.get_selection()
        selection.connect('changed', self.on_fact_selection_changed,
                          self.fact_store)
        self.popular_categories = [cat[0] for cat in storage.get_popular_categories()]

        self._gui.connect_signals(self)
        self.fact_tree.grab_focus()

        self.report_chooser = None
        self.do_graph()
        self.init_stats()


    
    def init_stats(self):
        self.get_widget("explore_frame").modify_bg(gtk.STATE_NORMAL,
                      gtk.gdk.Color(*[int(b*65536.0) for b in self.background]))

        if not self.stat_facts:
            self.stat_facts = storage.get_facts(dt.date(1970, 1, 1), dt.date.today())
        
        by_year = self._totals(self.stat_facts,
                               lambda fact: fact["start_time"].year,
                               lambda fact: 1)
        
        year_box = self.get_widget("year_box")
        for child in year_box.get_children():
            year_box.remove(child)
        
        class YearButton(gtk.ToggleButton):
            def __init__(self, label, year, on_clicked):
                gtk.ToggleButton.__init__(self, label)
                self.year = year
                self.connect("clicked", on_clicked)
        
        all_button = YearButton(_("All"), None, self.on_year_changed)
        year_box.pack_start(all_button)
        self.bubbling = True # TODO figure out how to properly work with togglebuttons as radiobuttons
        all_button.set_active(True)
        self.bubbling = False # TODO figure out how to properly work with togglebuttons as radiobuttons

        years = sorted(by_year.keys())
        for year in years:
            year_box.pack_start(YearButton(str(year), year, self.on_year_changed))

        year_box.show_all()




        self.chart_everything = charting.BarChart(value_format = "%.1f",
                                       bars_beveled = False,
                                       animate = False,
                                       background = self.background,
                                       show_labels = False)
        self.get_widget("explore_everything").add(self.chart_everything)


        self.chart_category_totals = charting.HorizontalBarChart(value_format = "%.1f",
                                                            bars_beveled = False,
                                                            background = self.background,
                                                            max_bar_width = 20,
                                                            legend_width = 70)
        self.get_widget("explore_category_totals").add(self.chart_category_totals)


        self.chart_weekday_totals = charting.HorizontalBarChart(value_format = "%.1f",
                                                            bars_beveled = False,
                                                            background = self.background,
                                                            max_bar_width = 20,
                                                            legend_width = 70)
        self.get_widget("explore_weekday_totals").add(self.chart_weekday_totals)

        self.chart_weekday_starts_ends = charting.HorizontalDayChart(bars_beveled = False,
                                                                animate = False,
                                                                background = self.background,
                                                                max_bar_width = 20,
                                                                legend_width = 70)
        self.get_widget("explore_weekday_starts_ends").add(self.chart_weekday_starts_ends)
        
        self.chart_category_starts_ends = charting.HorizontalDayChart(bars_beveled = False,
                                                                animate = False,
                                                                background = self.background,
                                                                max_bar_width = 20,
                                                                legend_width = 70)
        self.get_widget("explore_category_starts_ends").add(self.chart_category_starts_ends)


        #ah, just want summary look just like all the other text on the page
        class CairoText(graphics.Area):
            def __init__(self, background = None, fontsize = 10):
                graphics.Area.__init__(self)
                self.background = background
                self.text = ""
                self.fontsize = fontsize
                
            def set_text(self, text):
                self.text = text
                self.redraw_canvas()
                
            def _render(self):
                if self.background:
                    self.fill_area(0, 0, self.width, self.height, self.background)

                default_font = pango.FontDescription(gtk.Style().font_desc.to_string())
                default_font.set_size(self.fontsize * pango.SCALE)
                self.layout.set_font_description(default_font)
                
                #self.context.set_source_rgb(0,0,0)
                self.layout.set_markup(self.text)

                self.layout.set_width((self.width) * pango.SCALE)
                self.context.move_to(0,0)
                charting.set_color(self.context, charting.dark[8])
                
                self.context.show_layout(self.layout)


        self.explore_summary = CairoText(self.background)
        self.get_widget("explore_summary").add(self.explore_summary)
        self.get_widget("explore_summary").show_all()

    def on_pages_switch_page(self, notebook, page, pagenum):
        if pagenum == 1:
            year = None
            for child in self.get_widget("year_box").get_children():
                if child.get_active():
                    year = child.year
            
            self.stats(year)
        
        
    def on_year_changed(self, button):
        if self.bubbling: return
        
        for child in button.parent.get_children():
            if child != button and child.get_active():
                self.bubbling = True
                child.set_active(False)
                self.bubbling = False
        
        self.stats(button.year)
        
    def stats(self, year = None):
        facts = self.stat_facts
        if year:
            facts = filter(lambda fact: fact["start_time"].year == year,
                           facts)

        if not facts or (facts[-1]["start_time"] - facts[0]["start_time"]) < dt.timedelta(days=6):
            self.get_widget("statistics_box").hide()
            self.get_widget("explore_controls").hide()
            label = self.get_widget("not_enough_records_label")

            if not facts:
                label.set_text(_("""There is no data to generate statistics yet.
A week of usage would be nice!"""))
            else:
                label.set_text(_("Still collecting data - check back after a week has passed!"))

            label.show()
            return
        else:
            self.get_widget("statistics_box").show()
            self.get_widget("explore_controls").show()
            self.get_widget("not_enough_records_label").hide()

        # All dates in the scope
        just_totals = self._totals(facts,
                                   lambda fact: fact["start_time"].date(),
                                   lambda fact: fact["delta"].seconds / 60 / 60.0)
        just_totals_keys = sorted(just_totals.keys())
        
        just_totals = [just_totals[key][0] for key in just_totals_keys]
        just_totals_keys = [key.strftime("%d %m %Y") for key in just_totals_keys]

        self.chart_everything.plot(just_totals_keys, just_totals)


        # Totals by category
        categories = self._totals(facts,
                                  lambda fact: fact["category"],
                                  lambda fact: fact['delta'].seconds / 60 / 60.0)
        category_keys = sorted(categories.keys())
        categories = [categories[key][0] for key in category_keys]
        self.chart_category_totals.plot(category_keys, categories)
        

        # Totals by weekday
        weekdays = self._totals(facts,
                                  lambda fact: (fact["start_time"].weekday(),
                                                fact["start_time"].strftime("%a")),
                                  lambda fact: fact['delta'].seconds / 60 / 60.0)

        weekday_keys = sorted(weekdays.keys(), key = lambda x: x[0]) #sort 
        weekdays = [weekdays[key][0] for key in weekday_keys] #get values in the order
        weekday_keys = [key[1] for key in weekday_keys] #now remove the weekday and keep just the abbreviated one

        self.chart_weekday_totals.plot(weekday_keys, weekdays)



        # now we will try to figure out average start and end times.
        # first we need to group facts by date
        # they are already sorted in db, so we can rely on that
        by_weekday = {}
        for date, date_facts in groupby(facts, lambda fact: fact["start_time"].date()):
            date_facts = list(date_facts)
            weekday = (date_facts[0]["start_time"].weekday(),
                       date_facts[0]["start_time"].strftime("%a"))
            by_weekday.setdefault(weekday, {"min": [], "max": []})

            min_time = min([fact["start_time"].time() for fact in date_facts])
            by_weekday[weekday]["min"].append(min_time.minute + min_time.hour * 60)
            
            same_date_facts = [fact["end_time"].time() for fact in date_facts if fact["end_time"] and fact["start_time"].date() == fact["end_time"].date()]
            if same_date_facts:
                max_time = max(same_date_facts)
                by_weekday[weekday]["max"].append(max_time.minute + max_time.hour * 60)

        for day in by_weekday:
            by_weekday[day]["min"] = int(sum(by_weekday[day]["min"]) / float(len(by_weekday[day]["min"])))
            by_weekday[day]["min"] = dt.time(by_weekday[day]["min"] / 60, by_weekday[day]["min"] % 60)
                                             
            by_weekday[day]["max"] = int(sum(by_weekday[day]["max"]) / float(len(by_weekday[day]["max"])))
            by_weekday[day]["max"] = dt.time(by_weekday[day]["max"] / 60, by_weekday[day]["max"] % 60)

        min_weekday = min([by_weekday[day]["min"] for day in by_weekday])
        max_weekday = max([by_weekday[day]["max"] for day in by_weekday])

        weekday_keys = sorted(by_weekday.keys(), key = lambda x: x[0])
        weekdays = [(by_weekday[key]["min"], by_weekday[key]["max"])
                                                        for key in weekday_keys]
        
        weekday_keys = [key[1] for key in weekday_keys] # get rid of the weekday number as int


        # and now try to figure out average min and max times per day per category

        # now we will try to figure out average start and end times.
        # first we need to group facts by date
        # they are already sorted in db, so we can rely on that
        by_category = {}
        for date, date_facts in groupby(facts, lambda fact: fact["start_time"].date()):
            date_facts = sorted(list(date_facts), key = lambda x: x["category"])
            
            for category, category_facts in groupby(date_facts, lambda x: x["category"]):
                category_facts = list(category_facts)
                by_category.setdefault(category, {"min": [], "max": []})

                min_time = min([fact["start_time"].time() for fact in category_facts])
                by_category[category]["min"].append(min_time.minute + min_time.hour * 60)
            
                same_date_facts = [fact["end_time"].time() for fact in category_facts if fact["end_time"] and fact["start_time"].date() == fact["end_time"].date()]
                if same_date_facts:
                    max_time = max(same_date_facts)
                    by_category[category]["max"].append(max_time.minute + max_time.hour * 60)

        for key in by_category:
            by_category[key]["min"] = int(sum(by_category[key]["min"]) / float(len(by_category[key]["min"])))
            by_category[key]["min"] = dt.time(by_category[key]["min"] / 60, by_category[key]["min"] % 60)
                                             
            by_category[key]["max"] = int(sum(by_category[key]["max"]) / float(len(by_category[key]["max"])))
            by_category[key]["max"] = dt.time(by_category[key]["max"] / 60, by_category[key]["max"] % 60)

        min_category = min([by_category[day]["min"] for day in by_category])
        max_category = max([by_category[day]["max"] for day in by_category])


        category_keys = sorted(by_category.keys(), key = lambda x: x[0])
        categories = [(by_category[key]["min"], by_category[key]["max"])
                                                        for key in category_keys]


        #get starting and ending hours for graph and turn them into exact hours that divide by 3
        min_hour = min([min_weekday, min_category])
        min_hour = dt.time((min_hour.hour * 60 + min_hour.minute) / (3 * 60) * (3 * 60) / 60, 0)
        max_hour = max([max_weekday, max_category])
        max_hour = dt.time((max_hour.hour * 60 + max_hour.minute) / (3 * 60) * (3 * 60) / 60 + 3, 0) 

        self.chart_weekday_starts_ends.plot_day(weekday_keys, weekdays, min_hour, max_hour)
        self.chart_category_starts_ends.plot_day(category_keys, categories, min_hour, max_hour)


        #now the factoids!
        summary = ""

        # first record        
        if not year:
            #date format for case when year has not been selected
            first_date = _("%(first_b)s %(first_d)s, %(first_Y)s") % \
                               stuff.dateDict(facts[0]["start_time"], "first_")
        else:
            #date format when year has been selected
            first_date = _("%(first_b)s %(first_d)s") % \
                               stuff.dateDict(facts[0]["start_time"], "first_")

        summary += _("First activity was recorded on %s.") % \
                                                     ("<b>%s</b>" % first_date)
        
        # total time tracked
        total_delta = dt.timedelta(days=0)
        for fact in facts:
            total_delta += fact["delta"]
        
        if total_delta.days > 1:
            summary += " " + _("""Time tracked so far is %(human_days)s human days \
(%(human_years)s years) or %(working_days)s working days \
(%(working_years)s years).""") % \
            ({"human_days": ("<b>%d</b>" % total_delta.days),
              "human_years": ("<b>%.2f</b>" % (total_delta.days / 365.0)),
              "working_days": ("<b>%d</b>" % (total_delta.days * 3)), # 8 should be pretty much an average working day
              "working_years": ("<b>%.2f</b>" % (total_delta.days * 3 / 365.0))})
        

        # longest fact
        max_fact = None
        for fact in facts:
            if not max_fact or fact["delta"] > max_fact["delta"]:
                max_fact = fact

        datedict = stuff.dateDict(max_fact["start_time"], "max_")
        datedict["hours"] = "<b>%.1f</b>" % (max_fact["delta"].seconds / 60 / 60.0
                                                  + max_fact["delta"].days * 24)

        summary += "\n" + _("Longest continuous work happened on \
%(max_b)s %(max_d)s, %(max_Y)s and was %(hours)s hours.") % datedict

        # total records (in selected scope)
        summary += " " + _("There are %s records.") % ("<b>%d</b>" % len(facts))


        early_start, early_end = dt.time(5,0), dt.time(9,0)
        late_start, late_end = dt.time(20,0), dt.time(5,0)
        
        
        fact_count = len(facts)
        def percent(condition):
            matches = [fact for fact in facts if condition(fact)]
            return round(len(matches) / float(fact_count) * 100)
        
        
        early_percent = percent(lambda fact: early_start < fact["start_time"].time() < early_end)
        late_percent = percent(lambda fact: fact["start_time"].time() > late_start or fact["start_time"].time() < late_end)
        short_percent = percent(lambda fact: fact["delta"] <= dt.timedelta(seconds = 60 * 15))

        if fact_count < 100:
            summary += "\n\n" + _("Hamster would like to observe you some more!")
        elif early_percent >= 20:
            summary += "\n\n" + _("With %s percent of all facts starting before \
9am you seem to be an early bird." % ("<b>%d</b>" % early_percent))
        elif late_percent >= 20:
            summary += "\n\n" + _("With %s percent of all facts starting after \
11pm you seem to be a night owl." % ("<b>%d</b>" % late_percent))
        elif short_percent >= 20:
            summary += "\n\n" + _("With %s percent of all tasks being shorter \
than 15 minutes you seem to be a busy bee." % ("<b>%d</b>" % short_percent))

        self.explore_summary.set_text(summary)


    
    def _totals(self, iter, keyfunc, sumfunc):
        """groups items by field described in keyfunc and counts totals using value
           from sumfunc
        """
        data = sorted(iter, key=keyfunc)
    
        totals = {}
        max_total = -10000
        for k, group in groupby(data, keyfunc):
            totals[k] = sum([sumfunc(entry) for entry in group])
            max_total = max(max_total, totals[k])
        
        for total in totals: #add normalized version too
            totals[total] = (totals[total], totals[total] / float(max_total))
        
        return totals

    def more_on_left(self):
        z = min(round((self.end_date - self.start_date).days / 21.0)+1, 5)
        self.start_date = self.start_date - dt.timedelta(days = z)
        self.do_graph()
        
    def less_on_left(self):
        z = min(round((self.end_date - self.start_date).days / 21.0)+1, 5)
        self.start_date = self.start_date + dt.timedelta(days=z)
        self.do_graph()
        
    def setup_tree(self):
        def parent_painter(column, cell, model, iter):
            cell_text = model.get_value(iter, 1)
            if model.iter_parent(iter) is None:
                if model.get_path(iter) == (0,):
                    text = '<span weight="heavy">%s</span>' % cell_text
                else:
                    text = '<span weight="heavy" rise="-20000">%s</span>' % cell_text
                    
                cell.set_property('markup', text)
    
            else:
                activity_name = stuff.escape_pango(cell_text)
                description = stuff.escape_pango(model.get_value(iter, 4))
                category = stuff.escape_pango(model.get_value(iter, 5))

                markup = stuff.format_activity(activity_name, category, description, pad_description = True)            
                cell.set_property('markup', markup)

        def duration_painter(column, cell, model, iter):
            cell.set_property('xalign', 1)
            cell.set_property('yalign', 0)
    

            text = model.get_value(iter, 2)
            if model.iter_parent(iter) is None:
                if model.get_path(iter) == (0,):
                    text = '<span weight="heavy">%s</span>' % text
                else:
                    text = '<span weight="heavy" rise="-20000">%s</span>' % text
            cell.set_property('markup', text)
    

        self.fact_tree = self.get_widget("facts")
        self.fact_tree.set_headers_visible(False)
        self.fact_tree.set_tooltip_column(1)
        self.fact_tree.set_property("show-expanders", False)

        # name
        nameColumn = gtk.TreeViewColumn()
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()
        nameCell.set_property("ellipsize", pango.ELLIPSIZE_END)
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_cell_data_func(nameCell, parent_painter)
        self.fact_tree.append_column(nameColumn)

        # duration
        timeColumn = gtk.TreeViewColumn()
        timeCell = gtk.CellRendererText()
        timeColumn.pack_end(timeCell, True)
        timeColumn.set_cell_data_func(timeCell, duration_painter)




        self.fact_tree.append_column(timeColumn)
        
        self.fact_tree.set_model(self.fact_store)
        
        
    def locale_first_weekday(self):
        """figure if week starts on monday or sunday"""
        import os
        first_weekday = 6 #by default settle on monday

        try:
            process = os.popen("locale first_weekday week-1stday")
            week_offset, week_start = process.read().split('\n')[:2]
            process.close()
            week_start = dt.date(*time.strptime(week_start, "%Y%m%d")[:3])
            week_offset = dt.timedelta(int(week_offset) - 1)
            beginning = week_start + week_offset
            first_weekday = int(beginning.strftime("%w"))
        except:
            print "WARNING - Failed to get first weekday from locale"
            pass
            
        return first_weekday
        
    def get_facts(self, facts):
        self.fact_store.clear()
        totals = {}

        by_activity = {}
        by_category = {}
        by_day = {}

        for i in range((self.end_date - self.start_date).days  + 1):
            current_date = self.start_date + dt.timedelta(i)
            # date format in overview window fact listing
            # prefix is "o_",letter after prefix is regular python format. you can use all of them
            fact_date = _("%(o_A)s, %(o_b)s %(o_d)s") %  stuff.dateDict(current_date, "o_")

            day_row = self.fact_store.append(None, [-1,
                                                    fact_date,
                                                    "",
                                                    current_date.strftime('%Y-%m-%d'),
                                                    "", ""])
            by_day[self.start_date + dt.timedelta(i)] = {"duration": 0, "row_pointer": day_row}

                
                

        for fact in facts:
            start_date = fact["date"]

            duration = None
            if fact["delta"]:
                duration = 24 * fact["delta"].days + fact["delta"].seconds / 60

            self.fact_store.append(by_day[start_date]["row_pointer"],
                                   [fact["id"],
                                    fact["start_time"].strftime('%H:%M') + " " +
                                    fact["name"],
                                    stuff.format_duration(duration),
                                    fact["start_time"].strftime('%Y-%m-%d'),
                                    fact["description"],
                                    fact["category"]
                                    ])

            if duration:
                by_day[start_date]["duration"] += duration


        for day in by_day:
            self.fact_store.set_value(by_day[day]["row_pointer"], 2,
                stuff.format_duration(by_day[day]["duration"]))


        self.fact_tree.expand_all()
        
        self.get_widget("report_button").set_sensitive(len(facts) > 0)


        
    def get_totals(self, facts, all_days):
        # get list of used activities in interval
        activities = [act[0] for act in
              storage.get_interval_activity_ids(self.start_date, self.end_date)]

        # fill in the activity totals blanks
        # don't want to add ability to be able to specify color per bar
        # so we will be disguising our bar chart as multibar chart
        activity_totals = {}
        for act in activities:
            activity_totals[act] = {}
            for cat in self.popular_categories:
                activity_totals[act][cat] = 0

        # fill in the category totals blanks
        day_category_totals = {}
        for day in all_days:
            day_category_totals[day] = {}
            for cat in self.popular_categories:
                day_category_totals[day][cat] = 0
            
        #now we do the counting
        for fact in facts:
            duration = None
            start_date = fact['date']
            
            if fact["end_time"]: # not set if just started
                delta = fact["end_time"] - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60
            elif start_date == dt.date.today():
                delta = dt.datetime.now() - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60

            activity_totals[fact['name']][fact['category']] += duration or 0
            day_category_totals[start_date][fact['category']] += duration or 0


        # convert dictionaries into lists so we don't have to care about keys anymore
        res_categories = []
        for day in all_days:
            res_categories.append([day_category_totals[day][cat] / 60.0
                                            for cat in self.popular_categories])
            
        #sort activities by duration, longest first
        activity_totals = activity_totals.items()
        activity_totals = sorted(activity_totals,
                                 key = lambda(k,v): (max(v.values()), k),
                                 reverse = True)
        
        activities = [] #we have changed the order
        res_activities = []
        for act in activity_totals:
            activities.append(act[0])
            res_activities.append([act[1][cat] / 60.0
                                            for cat in self.popular_categories])

        return {'keys': activities, 'values': res_activities}, \
               {'keys': self.popular_categories, 'values': res_categories}
        

    def do_graph(self):
        dates_dict = stuff.dateDict(self.start_date, "start_")
        dates_dict.update(stuff.dateDict(self.end_date, "end_"))
        
        
        if self.start_date.year != self.end_date.year:
        
            # overview label if start and end years don't match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            overview_label = _(u"Overview for %(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif self.start_date.month != self.end_date.month:
            #overview label if start and end month do not match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            overview_label = _(u"Overview for %(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        else:
            #overview label for interval in same month
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            overview_label = _(u"Overview for %(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict

        if self.week_view.get_active():
            dayview_caption = _("Week")
        else:
            dayview_caption = _("Month")
        
        
        label = self.get_widget("overview_label")
        label.set_markup("<b>%s</b>" % overview_label)

        label2 = self.get_widget("dayview_caption")
        label2.set_markup("%s" % (dayview_caption))
        
        fact_list = storage.get_facts(self.start_date, self.end_date)

        self.get_facts(fact_list)
        
        if not fact_list:
            self.get_widget("graphs").hide()
            self.get_widget("no_data_label").show()
            return 
        else:
            self.get_widget("graphs").show()
            self.get_widget("no_data_label").hide()
            

        all_days = [self.start_date + dt.timedelta(i)
                    for i in range((self.end_date - self.start_date).days  + 1)]        

        activity_totals, day_category_totals = self.get_totals(fact_list, all_days)

        
        
        self.activity_chart.plot(activity_totals['keys'],
                                  activity_totals['values'],
                                  stack_keys = self.popular_categories)


        #show days or dates depending on scale
        if (self.end_date - self.start_date).days < 20:
            day_keys = [day.strftime("%a") for day in all_days]
        else:
            day_keys = [_("%(m_b)s %(m_d)s") %  stuff.dateDict(day, "m_") for day in all_days]


        self.day_chart.plot(day_keys, day_category_totals['values'],
                             stack_keys = day_category_totals['keys'])

        category_totals = [[sum(value) for value in zip(*day_category_totals['values'])]]
        
        category_keys = []
        for i in range(len(day_category_totals['keys'])):
            category_keys.append("%s %.1f" % (day_category_totals['keys'][i], category_totals[0][i]))
        

        self.category_chart.plot([_("Total")], category_totals,
                                  stack_keys = category_keys)


    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def on_prev_clicked(self, button):
        if self.week_view.get_active():
            self.start_date -= dt.timedelta(7)
            self.end_date -= dt.timedelta(7)
        
        elif self.month_view.get_active():
            self.end_date = self.start_date - dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.end_date.year, self.end_date.month)
            self.start_date = self.end_date - dt.timedelta(days_in_month - 1)

        self.view_date = self.start_date        
        self.do_graph()

    def on_next_clicked(self, button):
        if self.week_view.get_active():
            self.start_date += dt.timedelta(7)
            self.end_date += dt.timedelta(7)
        
        elif self.month_view.get_active():
            self.start_date = self.end_date + dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.start_date.year, self.start_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
        
        self.view_date = self.start_date
        self.do_graph()
    
    def on_home_clicked(self, button):
        self.view_date = dt.date.today()
        if self.week_view.get_active():
            self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
            self.start_date = self.start_date + dt.timedelta(self.locale_first_weekday())
            self.end_date = self.start_date + dt.timedelta(6)
        
        elif self.month_view.get_active():
            self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
            first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
        
        self.do_graph()
        
    def on_day_toggled(self, button):
        self.start_date = self.view_date
        self.end_date = self.view_date
        self.do_graph()

    def on_week_toggled(self, button):
        self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
        self.start_date = self.start_date + dt.timedelta(self.locale_first_weekday())

        self.end_date = self.start_date + dt.timedelta(6)
        self.do_graph()

        
    def on_month_toggled(self, button):
        self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
        first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
        self.end_date = self.start_date + dt.timedelta(days_in_month - 1)

        self.do_graph()
        
    def on_remove_clicked(self, button):
        self.delete_selected()

    def on_edit_clicked(self, button):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        if model[iter][0] == -1:
            return #not a fact

        custom_fact = CustomFactController(self, None, model[iter][0])
        custom_fact.show()

    def delete_selected(self):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        if model[iter][0] == -1:
            return #not a fact

        next_row = model.iter_next(iter)

        if next_row:
            selection.select_iter(next_row)
        else:
            path = model.get_path(iter)[0] - 1
            if path > 0:
                selection.select_path(path)

        storage.remove_fact(model[iter][0])

    """keyboard events"""
    def on_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Delete):
        self.delete_selected()
    
    def on_fact_selection_changed(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()

        id = -1
        if iter:
            id = model[iter][0]

        self.get_widget('remove').set_sensitive(id != -1)
        self.get_widget('edit').set_sensitive(id != -1)

        return True

    def on_facts_row_activated(self, tree, path, column):
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()
        custom_fact = CustomFactController(self, None, model[iter][0])
        custom_fact.show()
        
    def on_add_clicked(self, button):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        selected_date = self.view_date
        if iter:
            selected_date = model[iter][3].split("-")
            selected_date = dt.date(int(selected_date[0]),
                                    int(selected_date[1]),
                                    int(selected_date[2]))

        custom_fact = CustomFactController(self, selected_date)
        custom_fact.show()
        
    def init_report_dialog(self):
        chooser = self.get_widget('save_report_dialog')
        chooser.set_action(gtk.FILE_CHOOSER_ACTION_SAVE)
        """
        chooser.set
        
        chooser = gtk.FileChooserDialog(title = _("Save report - Time Tracker"),
                                        parent = None,
                                        buttons=(gtk.STOCK_CANCEL,
                                                 gtk.RESPONSE_CANCEL,
                                                 gtk.STOCK_SAVE,
                                                 gtk.RESPONSE_OK))
        """
        chooser.set_current_folder(os.path.expanduser("~"))

        filters = {}

        filter = gtk.FileFilter()
        filter.set_name(_("HTML Report"))
        filter.add_mime_type("text/html")
        filter.add_pattern("*.html")
        filter.add_pattern("*.htm")
        filters[filter] = "html"
        chooser.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("Tab Separated Values (TSV)"))
        filter.add_mime_type("text/plain")
        filter.add_pattern("*.tsv")
        filter.add_pattern("*.txt")
        filters[filter] = "tsv"
        chooser.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("XML"))
        filter.add_mime_type("text/xml")
        filter.add_pattern("*.xml")
        filters[filter] = "xml"
        chooser.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("iCal"))
        filter.add_mime_type("text/calendar")
        filter.add_pattern("*.ics")
        filters[filter] = "ical"
        chooser.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        chooser.add_filter(filter)
        
    def on_report_chosen(self, widget, format, path, start_date, end_date,
                                                                      category):
        self.report_chooser = None
        
        facts = storage.get_facts(start_date, end_date, category_id = category)
        reports.simple(facts,
                       self.start_date,
                       self.end_date,
                       format,
                       path)

        if format == ("html"):
            webbrowser.open_new("file://%s" % path)
        else:
            gtk.show_uri(gtk.gdk.Screen(),
                         "file://%s" % os.path.split(path)[0], 0L)

    def on_report_chooser_closed(self, widget):
        self.report_chooser = None
        
    def on_report_button_clicked(self, widget):
        if not self.report_chooser:
            self.report_chooser = ReportChooserDialog()
            self.report_chooser.connect("report-chosen", self.on_report_chosen)
            self.report_chooser.connect("report-chooser-closed", self.on_report_chooser_closed)
            self.report_chooser.show(self.start_date, self.end_date)
        else:
            self.report_chooser.present()
        
        
    def after_activity_update(self, widget, renames):
        self.do_graph()
    
    def after_fact_update(self, event, date):
        self.stat_facts = storage.get_facts(dt.date(1970, 1, 1), dt.date.today())
        self.popular_categories = [cat[0] for cat in storage.get_popular_categories()]
        
        if self.get_widget("pages").get_current_page() == 0:
            self.do_graph()
        else:
            self.stats()
        
    def on_close(self, widget, event):
        dispatcher.del_handler('activity_updated', self.after_activity_update)
        dispatcher.del_handler('day_updated', self.after_fact_update)
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

