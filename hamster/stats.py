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
import charting

from edit_activity import CustomFactController
import reports, widgets, graphics
from configuration import runtime
import webbrowser

from itertools import groupby
from gettext import ngettext

import datetime as dt
import calendar
import time
from hamster.i18n import C_

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
        filter.set_name(_("Tab-Separated Values (TSV)"))
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
        button_all = gtk.CheckButton(C_("categories", "All").encode("utf-8"))
        button_all.value = None
        button_all.set_active(True)
        
        def on_category_all_clicked(checkbox):
            active = checkbox.get_active()
            for checkbox in self.category_box.get_children():
                checkbox.set_active(active)
        
        button_all.connect("clicked", on_category_all_clicked)
        self.category_box.attach(button_all, 0, 1, 0, 1)

        categories = runtime.storage.get_category_list()
        col, row = 0, 0
        for category in categories:
            col +=1
            if col % 4 == 0:
                col = 0
                row +=1

            button = gtk.CheckButton(category['name'].encode("utf-8"))
            button.value = category['id']
            button.set_active(True)
            self.category_box.attach(button, col, col+1, row, row+1)

        

        response = self.dialog.show_all()

    def present(self):
        self.dialog.present()

    def on_save_button_clicked(self, widget):
        path, format = None,  None

        format = "html"
        if self.dialog.get_filter() in self.filters:
            format = self.filters[self.dialog.get_filter()]
        path = self.dialog.get_filename()
        
        categories = []
        for button in self.category_box.get_children():
            if button.get_active():
                categories.append(button.value)
        
        if None in categories:
            categories = None # nothing is everything
        
        # format, path, start_date, end_date
        self.emit("report-chosen", format, path,
                           self.start_date.get_date().date(),
                           self.end_date.get_date().date(),
                           categories)
        self.dialog.destroy()
        

    def on_cancel_button_clicked(self, widget):
        self.emit("report-chooser-closed")
        self.dialog.destroy()

class TimeLine(graphics.Area):
    MODE_YEAR = 0
    MODE_MONTH = 1
    MODE_WEEK = 1
    MODE_DAY = 3
    def __init__(self):
        graphics.Area.__init__(self)
        self.start_date, self.end_date = None, None
        self.draw_mode = None
        self.max_hours = None
        
    
    def draw(self, facts):
        import itertools
        self.facts = {}
        for date, date_facts in itertools.groupby(facts, lambda x: x["start_time"].date()):
            date_facts = list(date_facts)
            self.facts[date] = date_facts
            self.max_hours = max(self.max_hours,
                                 sum([fact["delta"].seconds / 60 / float(60) +
                               fact["delta"].days * 24 for fact in date_facts]))
        
        start_date = facts[0]["start_time"].date()
        end_date = facts[-1]["start_time"].date()

        self.draw_mode = self.MODE_YEAR
        self.start_date = start_date.replace(month=1, day=1)
        self.end_date = end_date.replace(month=12, day=31)
        

        """
        #TODO - for now we have only the year mode        
        if start_date.year != end_date.year or start_date.month != end_date.month:
            self.draw_mode = self.MODE_YEAR
            self.start_date = start_date.replace(month=1, day=1)
            self.end_date = end_date.replace(month=12, day=31)
        elif start_date.strftime("%W") != end_date.strftime("%W"):
            self.draw_mode = self.MODE_MONTH
            self.start_date = start_date.replace(day=1)
            self.end_date = end_date.replace(date =
                                    calendar.monthrange(self.end_date.year,
                                                        self.end_date.month)[1])
        elif start_date != end_date:
            self.draw_mode = self.MODE_WEEK
        else:
            self.draw_mode = self.MODE_DAY
        """
        
        self.redraw_canvas()
        
        
    def _render(self):
        import calendar
        
        if self.draw_mode != self.MODE_YEAR:
            return

        self.fill_area(0, 0, self.width, self.height, (0.975,0.975,0.975))
        self.set_color((100,100,100))

        self.set_value_range(x_min = 1, x_max = (self.end_date - self.start_date).days)        
        month_label_fits = True
        for month in range(1, 13):
            self.layout.set_text(calendar.month_abbr[month])
            label_w, label_h = self.layout.get_pixel_size()
            if label_w * 2 > self.x_factor * 30:
                month_label_fits = False
                break
        
        
        ticker_date = self.start_date
        
        year_pos = 0
        
        for year in range(self.start_date.year, self.end_date.year + 1):
            #due to how things lay over, we are putting labels on backwards, so that they don't overlap
            
            self.context.set_line_width(1)
            for month in range(1, 13):
                for day in range(1, calendar.monthrange(year, month)[1] + 1):
                    ticker_pos = year_pos + ticker_date.timetuple().tm_yday
                    
                    #if ticker_date.weekday() in [0, 6]:
                    #    self.fill_area(ticker_pos * self.x_factor + 1, 20, self.x_factor, self.height - 20, (240, 240, 240))
                    #    self.context.stroke()
                        
    
                    if self.x_factor > 5:
                        self.move_to(ticker_pos, self.height - 20)
                        self.line_to(ticker_pos, self.height)
                   
                        self.layout.set_text(ticker_date.strftime("%d"))
                        label_w, label_h = self.layout.get_pixel_size()
                        
                        if label_w < self.x_factor / 1.2: #if label fits
                            self.context.move_to(self.get_pixel(ticker_pos) + 2,
                                                 self.height - 20)
                            self.context.show_layout(self.layout)
                    
                        self.context.stroke()
                        
                    #now facts
                    facts_today = self.facts.get(ticker_date, [])
                    if facts_today:
                        total_length = dt.timedelta()
                        for fact in facts_today:
                            total_length += fact["delta"]
                        total_length = total_length.seconds / 60 / 60.0 + total_length.days * 24
                        total_length = total_length / float(self.max_hours) * self.height - 16
                        self.fill_area(ticker_pos * self.x_factor,
                                       self.height - total_length,
                                       self.x_factor, total_length,
                                       (190,190,190))


                        

                    ticker_date += dt.timedelta(1)
                
            
                
                if month_label_fits:
                    #roll back a little
                    month_pos = ticker_pos - calendar.monthrange(year, month)[1] + 1

                    self.move_to(month_pos, 0)
                    #self.line_to(month_pos, 20)
                    
                    self.layout.set_text(dt.date(year, month, 1).strftime("%b"))
    
                    self.move_to(month_pos, 0)
                    self.context.show_layout(self.layout)


    
            
    
            self.layout.set_text("%d" % year)
            label_w, label_h = self.layout.get_pixel_size()
                        
            self.move_to(year_pos + 2 / self.x_factor, month_label_fits * label_h * 1.2)
    
            self.context.show_layout(self.layout)
            
            self.context.stroke()

            year_pos = ticker_pos #save current state for next year



class StatsViewer(object):
    def __init__(self, parent = None):
        self.parent = parent# determine if app should shut down on close
        self._gui = stuff.load_ui_file("stats.ui")
        self.window = self.get_widget('stats_window')
        self.stat_facts = None

        #id, caption, duration, date (invisible), description, category
        self.fact_store = gtk.TreeStore(int, str, str, str, str, str, gobject.TYPE_PYOBJECT) 
        self.setup_tree()
        
        
        #graphs
        self.background = (0.975, 0.975, 0.975)
        self.get_widget("graph_frame").modify_bg(gtk.STATE_NORMAL,
                      gtk.gdk.Color(*[int(b*65536.0) for b in self.background]))
        self.get_widget("explore_frame").modify_bg(gtk.STATE_NORMAL,
                      gtk.gdk.Color(*[int(b*65536.0) for b in self.background]))


        x_offset = 90 # align all graphs to the left edge
        
        self.category_chart = charting.BarChart(background = self.background,
                                             bar_base_color = (238,221,221),
                                             legend_width = x_offset,
                                             max_bar_width = 35,
                                             show_stack_labels = True
                                             )
        self.get_widget("totals_by_category").add(self.category_chart)
        

        self.day_chart = charting.BarChart(background = self.background,
                                           bar_base_color = (220, 220, 220),
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
                                      dt.timedelta(stuff.locale_first_weekday())
        
        self.end_date = self.start_date + dt.timedelta(6)

        
        self.week_view = self.get_widget("week")
        self.month_view = self.get_widget("month")
        self.month_view.set_group(self.week_view)
        self.day_view = self.get_widget("day")
        self.day_view.set_group(self.week_view)
        
        #initiate the form in the week view
        self.week_view.set_active(True)


        runtime.dispatcher.add_handler('activity_updated', self.after_activity_update)
        runtime.dispatcher.add_handler('day_updated', self.after_fact_update)

        selection = self.fact_tree.get_selection()
        selection.connect('changed', self.on_fact_selection_changed,
                          self.fact_store)
        self.popular_categories = [cat[0] for cat in runtime.storage.get_popular_categories()]

        self._gui.connect_signals(self)
        self.fact_tree.grab_focus()

        self.timeline = TimeLine()
        self.get_widget("explore_everything").add(self.timeline)
        self.get_widget("explore_everything").show_all()


        self.report_chooser = None
        self.do_graph()
        self.init_stats()

    def init_stats(self):
        self.stat_facts = runtime.storage.get_facts(dt.date(1970, 1, 1), dt.date.today())
        
        by_year = stuff.totals(self.stat_facts,
                               lambda fact: fact["start_time"].year,
                               lambda fact: 1)
        
        year_box = self.get_widget("year_box")
        class YearButton(gtk.ToggleButton):
            def __init__(self, label, year, on_clicked):
                gtk.ToggleButton.__init__(self, label)
                self.year = year
                self.connect("clicked", on_clicked)
        
        all_button = YearButton(C_("years", "All").encode("utf-8"),
                                None,
                                self.on_year_changed)
        year_box.pack_start(all_button)
        self.bubbling = True # TODO figure out how to properly work with togglebuttons as radiobuttons
        all_button.set_active(True)
        self.bubbling = False # TODO figure out how to properly work with togglebuttons as radiobuttons

        years = sorted(by_year.keys())
        for year in years:
            year_box.pack_start(YearButton(str(year), year, self.on_year_changed))

        year_box.show_all()

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
                self.set_color(charting.graphics.Colors.aluminium[5])
                
                self.context.show_layout(self.layout)

        self.explore_summary = CairoText(self.background)
        self.get_widget("explore_summary").add(self.explore_summary)
        self.get_widget("explore_summary").show_all()

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
                label.set_text(_("Still collecting data — check back after a week has passed!"))

            label.show()
            return
        else:
            self.get_widget("statistics_box").show()
            self.get_widget("explore_controls").show()
            self.get_widget("not_enough_records_label").hide()

        # All dates in the scope
        self.timeline.draw(facts)


        # Totals by category
        categories = stuff.totals(facts,
                                  lambda fact: fact["category"],
                                  lambda fact: fact['delta'].seconds / 60 / 60.0)
        category_keys = sorted(categories.keys())
        categories = [categories[key] for key in category_keys]
        self.chart_category_totals.plot(category_keys, categories)
        
        # Totals by weekday
        weekdays = stuff.totals(facts,
                                lambda fact: (fact["start_time"].weekday(),
                                              fact["start_time"].strftime("%a")),
                                lambda fact: fact['delta'].seconds / 60 / 60.0)
        
        weekday_keys = sorted(weekdays.keys(), key = lambda x: x[0]) #sort 
        weekdays = [weekdays[key] for key in weekday_keys] #get values in the order
        weekday_keys = [key[1] for key in weekday_keys] #now remove the weekday and keep just the abbreviated one
        self.chart_weekday_totals.plot(weekday_keys, weekdays)


        split_minutes = 5 * 60 + 30 #the mystical hamster midnight
        
        # starts and ends by weekday
        by_weekday = {}
        for date, date_facts in groupby(facts, lambda fact: fact["start_time"].date()):
            date_facts = list(date_facts)
            weekday = (date_facts[0]["start_time"].weekday(),
                       date_facts[0]["start_time"].strftime("%a"))
            by_weekday.setdefault(weekday, [])
            
            start_times, end_times = [], []
            for fact in date_facts:
                start_time = fact["start_time"].time()
                start_time = start_time.hour * 60 + start_time.minute
                if fact["end_time"]:
                    end_time = fact["end_time"].time()
                    end_time = end_time.hour * 60 + end_time.minute
                
                    if start_time < split_minutes:
                        start_time += 24 * 60
                    if end_time < start_time:
                        end_time += 24 * 60
                    
                    start_times.append(start_time)
                    end_times.append(end_time)
            if start_times and end_times:            
                by_weekday[weekday].append((min(start_times), max(end_times)))


        for day in by_weekday:
            by_weekday[day] = (sum([fact[0] for fact in by_weekday[day]]) / len(by_weekday[day]),
                               sum([fact[1] for fact in by_weekday[day]]) / len(by_weekday[day]))

        min_weekday = min([by_weekday[day][0] for day in by_weekday])
        max_weekday = max([by_weekday[day][1] for day in by_weekday])


        weekday_keys = sorted(by_weekday.keys(), key = lambda x: x[0])
        weekdays = [by_weekday[key] for key in weekday_keys]
        weekday_keys = [key[1] for key in weekday_keys] # get rid of the weekday number as int

        
        # starts and ends by category
        by_category = {}
        for date, date_facts in groupby(facts, lambda fact: fact["start_time"].date()):
            date_facts = sorted(list(date_facts), key = lambda x: x["category"])
            
            for category, category_facts in groupby(date_facts, lambda x: x["category"]):
                category_facts = list(category_facts)
                by_category.setdefault(category, [])
                
                start_times, end_times = [], []
                for fact in category_facts:
                    start_time = fact["start_time"]
                    start_time = start_time.hour * 60 + start_time.minute
                    if fact["end_time"]:
                        end_time = fact["end_time"].time()
                        end_time = end_time.hour * 60 + end_time.minute
                        
                        if start_time < split_minutes:
                            start_time += 24 * 60
                        if end_time < start_time:
                            end_time += 24 * 60

                        start_times.append(start_time)
                        end_times.append(end_time)

                if start_times and end_times:            
                    by_category[category].append((min(start_times), max(end_times)))

        for cat in by_category:
            by_category[cat] = (sum([fact[0] for fact in by_category[cat]]) / len(by_category[cat]),
                                sum([fact[1] for fact in by_category[cat]]) / len(by_category[cat]))

        min_category = min([by_category[day][0] for day in by_category])
        max_category = max([by_category[day][1] for day in by_category])

        category_keys = sorted(by_category.keys(), key = lambda x: x[0])
        categories = [by_category[key] for key in category_keys]


        #get starting and ending hours for graph and turn them into exact hours that divide by 3
        min_hour = min([min_weekday, min_category]) / 60 * 60
        max_hour = max([max_weekday, max_category]) / 60 * 60

        self.chart_weekday_starts_ends.plot_day(weekday_keys, weekdays, min_hour, max_hour)
        self.chart_category_starts_ends.plot_day(category_keys, categories, min_hour, max_hour)


        #now the factoids!
        summary = ""

        # first record        
        if not year:
            # date format for the first record if the year has not been selected
            # Using python datetime formatting syntax. See:
            # http://docs.python.org/library/time.html#time.strftime
            first_date = facts[0]["start_time"].strftime(C_("first record", "%b %d, %Y"))
        else:
            # date of first record when year has been selected
            # Using python datetime formatting syntax. See:
            # http://docs.python.org/library/time.html#time.strftime
            first_date = facts[0]["start_time"].strftime(C_("first record", "%b %d"))

        summary += _("First activity was recorded on %s.") % \
                                                     ("<b>%s</b>" % first_date)
        
        # total time tracked
        total_delta = dt.timedelta(days=0)
        for fact in facts:
            total_delta += fact["delta"]
        
        if total_delta.days > 1:
            human_years_str = ngettext("%(num)s year",
                                       "%(num)s years",
                                       total_delta.days / 365) % {
                              'num': "<b>%.2f</b>" % (total_delta.days / 365.0)}
            working_years_str = ngettext("%(num)s year",
                                         "%(num)s years",
                                         total_delta.days * 3 / 365) % {
                         'num': "<b>%.2f</b>" % (total_delta.days * 3 / 365.0) }
            #FIXME: difficult string to properly pluralize
            summary += " " + _("""Time tracked so far is %(human_days)s human days \
(%(human_years)s) or %(working_days)s working days (%(working_years)s).""") % {
              "human_days": ("<b>%d</b>" % total_delta.days),
              "human_years": human_years_str,
              "working_days": ("<b>%d</b>" % (total_delta.days * 3)), # 8 should be pretty much an average working day
              "working_years": working_years_str }
        

        # longest fact
        max_fact = None
        for fact in facts:
            if not max_fact or fact["delta"] > max_fact["delta"]:
                max_fact = fact

        longest_date = max_fact["start_time"].strftime(
            # How the date of the longest activity should be displayed in statistics
            # Using python datetime formatting syntax. See:
            # http://docs.python.org/library/time.html#time.strftime
            C_("date of the longest activity", "%b %d, %Y"))
        
        num_hours = max_fact["delta"].seconds / 60 / 60.0 + max_fact["delta"].days * 24
        hours = "<b>%.1f</b>" % (num_hours)
        
        summary += "\n" + ngettext("Longest continuous work happened on \
%(date)s and was %(hours)s hour.",
                                  "Longest continuous work happened on \
%(date)s and was %(hours)s hours.",
                                  int(num_hours)) % {"date": longest_date,
                                                     "hours": hours}

        # total records (in selected scope)
        summary += " " + ngettext("There is %s record.",
                                  "There are %s records.",
                                  len(facts)) % ("<b>%d</b>" % len(facts))


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

                markup = stuff.format_activity(activity_name,
                                               category,
                                               description,
                                               pad_description = True)            
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
    
    def on_graph_frame_size_allocate(self, widget, new_size):
        w = min(new_size.width / 4, 200)
        
        self.activity_chart.legend_width = w
        self.category_chart.legend_width = w
        self.get_widget("totals_by_category").set_size_request(w + 40, -1)
    
    def fill_tree(self, facts):
        day_dict = {}
        for day, facts in groupby(facts, lambda fact: fact["date"]):
            day_dict[day] = sorted(list(facts),
                                   key=lambda fact: fact["start_time"])
        
        for i in range((self.end_date - self.start_date).days  + 1):
            current_date = self.start_date + dt.timedelta(i)
            
            # Date format for the label in overview window fact listing
            # Using python datetime formatting syntax. See:
            # http://docs.python.org/library/time.html#time.strftime
            fact_date = current_date.strftime(C_("overview list", "%A, %b %d"))
            
            day_total = dt.timedelta()
            for fact in day_dict.get(current_date, []):
                day_total += fact["delta"]

            day_row = self.fact_store.append(None,
                                             [-1,
                                              fact_date,
                                              stuff.format_duration(day_total),
                                              current_date.strftime('%Y-%m-%d'),
                                              "",
                                              "",
                                              None])

            for fact in day_dict.get(current_date, []):
                self.fact_store.append(day_row,
                                       [fact["id"],
                                        fact["start_time"].strftime('%H:%M') + " " +
                                        fact["name"],
                                        stuff.format_duration(fact["delta"]),
                                        fact["start_time"].strftime('%Y-%m-%d'),
                                        fact["description"],
                                        fact["category"],
                                        fact
                                        ])

        self.fact_tree.expand_all()

        
    def do_charts(self, facts):
        all_categories = self.popular_categories
        
        
        #the single "totals" (by category) bar
        category_sums = stuff.totals(facts, lambda fact: fact["category"],
                      lambda fact: stuff.duration_minutes(fact["delta"]) / 60.0)
        category_totals = [category_sums.get(cat, 0)
                                                      for cat in all_categories]
        category_keys = ["%s %.1f" % (cat, category_sums.get(cat, 0.0))
                                                      for cat in all_categories]
        self.category_chart.plot([_("Total")],
                                 [category_totals],
                                 stack_keys = category_keys)
        
        # day / category chart
        all_days = [self.start_date + dt.timedelta(i)
                    for i in range((self.end_date - self.start_date).days  + 1)]        

        by_date_cat = stuff.totals(facts,
                                   lambda fact: (fact["date"],
                                                 fact["category"]),
                                   lambda fact: stuff.duration_minutes(fact["delta"]) / 60.0)
        res = [[by_date_cat.get((day, cat), 0)
                                 for cat in all_categories] for day in all_days]

        #show days or dates depending on scale
        if (self.end_date - self.start_date).days < 20:
            day_keys = [day.strftime("%a") for day in all_days]
        else:
            # date format used in the overview graph when month view is selected
            # Using python datetime formatting syntax. See:
            # http://docs.python.org/library/time.html#time.strftime
            day_keys = [day.strftime(C_("overview graph", "%b %d"))
                                                            for day in all_days]

        self.day_chart.plot(day_keys, res, stack_keys = all_categories)


        #totals by activity, disguised under a stacked bar chart to get category colors
        activity_sums = stuff.totals(facts,
                                     lambda fact: (fact["name"],
                                                   fact["category"]),
                                     lambda fact: stuff.duration_minutes(fact["delta"]))
        by_duration = sorted(activity_sums.items(),
                             key = lambda x: x[1],
                             reverse = True)
        by_duration_keys = [entry[0][0] for entry in by_duration]

        category_sums = [[entry[1] / 60.0 * (entry[0][1] == cat)
                            for cat in all_categories] for entry in by_duration]
        self.activity_chart.plot(by_duration_keys,
                                 category_sums,
                                 stack_keys = all_categories)
        

    def set_title(self):
        if self.day_view.get_active():
            # date format for overview label when only single day is visible
            # Using python datetime formatting syntax. See:
            # http://docs.python.org/library/time.html#time.strftime
            start_date_str = self.view_date.strftime(C_("single day overview",
                                                        "%B %d, %Y"))
            # Overview label if looking on single day
            overview_label = _(u"Overview for %(date)s") % \
                                                      ({"date": start_date_str})
        else:
            dates_dict = stuff.dateDict(self.start_date, "start_")
            dates_dict.update(stuff.dateDict(self.end_date, "end_"))
            
            if self.start_date.year != self.end_date.year:
                # overview label if start and end years don't match
                # letter after prefixes (start_, end_) is the one of
                # standard python date formatting ones- you can use all of them
                # see http://docs.python.org/library/time.html#time.strftime
                overview_label = _(u"Overview for %(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
            elif self.start_date.month != self.end_date.month:
                # overview label if start and end month do not match
                # letter after prefixes (start_, end_) is the one of
                # standard python date formatting ones- you can use all of them
                # see http://docs.python.org/library/time.html#time.strftime
                overview_label = _(u"Overview for %(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
            else:
                # overview label for interval in same month
                # letter after prefixes (start_, end_) is the one of
                # standard python date formatting ones- you can use all of them
                # see http://docs.python.org/library/time.html#time.strftime
                overview_label = _(u"Overview for %(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict

        if self.week_view.get_active():
            dayview_caption = _("Week")
        elif self.month_view.get_active():
            dayview_caption = _("Month")
        else:
            dayview_caption = _("Day")
        
        self.get_widget("overview_label").set_markup("<b>%s</b>" % overview_label)
        self.get_widget("dayview_caption").set_markup("%s" % (dayview_caption))
        

    def do_graph(self):
        self.set_title()
        
        if self.day_view.get_active():
            facts = runtime.storage.get_facts(self.view_date)
        else:
            facts = runtime.storage.get_facts(self.start_date, self.end_date)


        self.get_widget("report_button").set_sensitive(len(facts) > 0)
        self.fact_store.clear()
        
        self.fill_tree(facts)

        if not facts:
            self.get_widget("graphs").hide()
            self.get_widget("no_data_label").show()
            return 


        self.get_widget("no_data_label").hide()
        self.get_widget("graphs").show()
        self.do_charts(facts)
            


    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def on_pages_switch_page(self, notebook, page, pagenum):
        if pagenum == 1:
            year = None
            for child in self.get_widget("year_box").get_children():
                if child.get_active():
                    year = child.year
            
            self.stats(year)
        else:
            self.do_graph()
        
    def on_year_changed(self, button):
        if self.bubbling: return
        
        for child in button.parent.get_children():
            if child != button and child.get_active():
                self.bubbling = True
                child.set_active(False)
                self.bubbling = False
        
        self.stats(button.year)

    def on_prev_clicked(self, button):
        if self.day_view.get_active():
            self.view_date -= dt.timedelta(1)
            if self.view_date < self.start_date:
                self.start_date -= dt.timedelta(7)
                self.end_date -= dt.timedelta(7)
        else:
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
        if self.day_view.get_active():
            self.view_date += dt.timedelta(1)
            if self.view_date > self.end_date:
                self.start_date += dt.timedelta(7)
                self.end_date += dt.timedelta(7)
        else:
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
            self.start_date = self.start_date + dt.timedelta(stuff.locale_first_weekday())
            self.end_date = self.start_date + dt.timedelta(6)
        
        elif self.month_view.get_active():
            self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
            first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
        
        self.do_graph()
        
    def on_day_toggled(self, button):
        self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
        self.start_date = self.start_date + dt.timedelta(stuff.locale_first_weekday())
        self.end_date = self.start_date + dt.timedelta(6)
        
        self.get_widget("prev").set_tooltip_text(_("Previous day"))
        self.get_widget("next").set_tooltip_text(_("Next day"))
        self.get_widget("home").set_tooltip_text(_("Today"))
        self.get_widget("home").set_label(_("Today"))
        
        self.do_graph()

    def on_week_toggled(self, button):
        self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
        self.start_date = self.start_date + dt.timedelta(stuff.locale_first_weekday())
        self.end_date = self.start_date + dt.timedelta(6)

        self.get_widget("prev").set_tooltip_text(_("Previous week"))
        self.get_widget("next").set_tooltip_text(_("Next week"))
        self.get_widget("home").set_tooltip_text(_("This week"))
        self.get_widget("home").set_label(_("This Week"))
        self.do_graph()

        
    def on_month_toggled(self, button):
        self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
        first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
        self.end_date = self.start_date + dt.timedelta(days_in_month - 1)

        self.get_widget("prev").set_tooltip_text(_("Previous month"))
        self.get_widget("next").set_tooltip_text(_("Next month"))
        self.get_widget("home").set_tooltip_text(_("This month"))
        self.get_widget("home").set_label(_("This Month"))
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

        runtime.storage.remove_fact(model[iter][0])

    def copy_selected(self):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        fact = model[iter][6]
        if not fact:
            return #not a fact

        fact_str = "%s-%s %s" % (fact["start_time"].strftime("%H:%M"),
                               (fact["end_time"] or dt.datetime.now()).strftime("%H:%M"),
                               fact["name"])

        if fact["category"]:
            fact_str += "@%s" % fact["category"]

        if fact["description"]:
            fact_str += ", %s" % fact["description"]

        clipboard = gtk.Clipboard()
        clipboard.set_text(fact_str)
    
    def check_clipboard(self):
        clipboard = gtk.Clipboard()
        clipboard.request_text(self.on_clipboard_text)
    
    def on_clipboard_text(self, clipboard, text, data):
        # first check that we have a date selected
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        selected_date = self.view_date
        if iter:
            selected_date = model[iter][3].split("-")
            selected_date = dt.date(int(selected_date[0]),
                                    int(selected_date[1]),
                                    int(selected_date[2]))
        if not selected_date:
            return
        
        res = stuff.parse_activity_input(text)

        if res.start_time is None or res.end_time is None:
            return
        
        start_time = res.start_time.replace(year = selected_date.year,
                                            month = selected_date.month,
                                            day = selected_date.day)
        end_time = res.end_time.replace(year = selected_date.year,
                                               month = selected_date.month,
                                               day = selected_date.day)
    
        activity_name = res.activity_name
        if res.category_name:
            activity_name += "@%s" % res.category_name
            
        if res.description:
            activity_name += ", %s" % res.description

        activity_name = activity_name.decode("utf-8")

        # TODO - set cursor to the pasted entry when done
        # TODO - revisit parsing of selected date
        added_fact = runtime.storage.add_fact(activity_name, start_time, end_time)
        

    """keyboard events"""
    def on_key_pressed(self, tree, event):
        if (event.keyval == gtk.keysyms.Delete):
            self.delete_selected()
        elif event.keyval == gtk.keysyms.c and event.state & gtk.gdk.CONTROL_MASK:
            self.copy_selected()
        elif event.keyval == gtk.keysyms.v and event.state & gtk.gdk.CONTROL_MASK:
            self.check_clipboard()
    
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
        filter.set_name(_("Tab-Separated Values (TSV)"))
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
                                                                    categories):
        self.report_chooser = None
        
        facts = runtime.storage.get_facts(start_date, end_date, category_id = categories)
        reports.simple(facts,
                       start_date,
                       end_date,
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
            self.report_chooser.connect("report-chooser-closed",
                                        self.on_report_chooser_closed)
            self.report_chooser.show(self.start_date, self.end_date)
        else:
            self.report_chooser.present()
        
        
    def after_activity_update(self, widget, renames):
        self.do_graph()
    
    def after_fact_update(self, event, date):
        self.stat_facts = runtime.storage.get_facts(dt.date(1970, 1, 1), dt.date.today())
        self.popular_categories = [cat[0] for cat in runtime.storage.get_popular_categories()]
        
        if self.get_widget("pages").get_current_page() == 0:
            self.do_graph()
        else:
            self.stats()
        
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

