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
import time
import datetime as dt
import calendar
from itertools import groupby
from gettext import ngettext

import gtk, gobject
import pango

import stuff, charting, graphics, widgets
from configuration import runtime, conf

from hamster.i18n import C_

class Stats(object):
    def __init__(self, parent = None):
        self._gui = stuff.load_ui_file("stats.ui")
        self.report_chooser = None
        self.window = self.get_widget("stats_window")

        self.parent = parent# determine if app should shut down on close

        self.stat_facts = None

        day_start = conf.get("day_start_minutes")
        day_start = dt.time(day_start / 60, day_start % 60)
        self.timechart = widgets.TimeChart()
        self.timechart.day_start = day_start

        self.get_widget("explore_everything").add(self.timechart)
        self.get_widget("explore_everything").show_all()

        runtime.storage.connect('activities-changed',self.after_fact_update)
        runtime.storage.connect('facts-changed',self.after_fact_update)

        self.init_stats()

        self.window.set_position(gtk.WIN_POS_CENTER)

        self._gui.connect_signals(self)
        self.window.show_all()
        self.stats()



    def init_stats(self):
        self.stat_facts = runtime.storage.get_facts(dt.date(1970, 1, 2), dt.date.today())

        if not self.stat_facts or self.stat_facts[-1]["start_time"].year == self.stat_facts[0]["start_time"].year:
            self.get_widget("explore_controls").hide()
        else:
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

        self.chart_category_totals = charting.Chart(value_format = "%.1f",
                                                       max_bar_width = 20,
                                                       legend_width = 70,
                                                       interactive = False)
        self.get_widget("explore_category_totals").add(self.chart_category_totals)


        self.chart_weekday_totals = charting.Chart(value_format = "%.1f",
                                                      max_bar_width = 20,
                                                      legend_width = 70,
                                                      interactive = False)
        self.get_widget("explore_weekday_totals").add(self.chart_weekday_totals)

        self.chart_weekday_starts_ends = charting.HorizontalDayChart(max_bar_width = 20,
                                                                     legend_width = 70)
        self.get_widget("explore_weekday_starts_ends").add(self.chart_weekday_starts_ends)

        self.chart_category_starts_ends = charting.HorizontalDayChart(max_bar_width = 20,
                                                                      legend_width = 70)
        self.get_widget("explore_category_starts_ends").add(self.chart_category_starts_ends)




        #ah, just want summary look just like all the other text on the page
        class CairoText(graphics.Scene):
            def __init__(self, fontsize = 10):
                graphics.Scene.__init__(self)
                self.text = ""
                self.fontsize = fontsize

            def set_text(self, text):
                self.text = text
                self.redraw()

            def on_expose(self):
                # now for the text - we want reduced contrast for relaxed visuals
                fg_color = self.get_style().fg[gtk.STATE_NORMAL].to_string()
                if self.colors.is_light(fg_color):
                    label_color = self.colors.darker(fg_color,  80)
                else:
                    label_color = self.colors.darker(fg_color,  -80)

                default_font = pango.FontDescription(gtk.Style().font_desc.to_string())
                default_font.set_size(self.fontsize * pango.SCALE)
                self.layout.set_font_description(default_font)

                #self.context.set_source_rgb(0,0,0)
                self.layout.set_markup(self.text)

                self.layout.set_width((self.width) * pango.SCALE)
                self.context.move_to(0,0)
                self.set_color(label_color)

                self.context.show_layout(self.layout)

        self.explore_summary = CairoText()
        self.get_widget("explore_summary").add(self.explore_summary)
        self.get_widget("explore_summary").show_all()

    def stats(self, year = None):
        facts = self.stat_facts
        if year:
            facts = filter(lambda fact: fact["start_time"].year == year,
                           facts)

        if not facts or (facts[-1]["start_time"] - facts[0]["start_time"]) < dt.timedelta(days=6):
            self.get_widget("statistics_box").hide()
            #self.get_widget("explore_controls").hide()
            label = self.get_widget("not_enough_records_label")

            if not facts:
                label.set_text(_("""There is no data to generate statistics yet.
A week of usage would be nice!"""))
            else:
                label.set_text(_("Collecting data — check back after a week has passed!"))

            label.show()
            return
        else:
            self.get_widget("statistics_box").show()
            self.get_widget("explore_controls").show()
            self.get_widget("not_enough_records_label").hide()

        # All dates in the scope
        durations = [(fact["start_time"], fact["delta"]) for fact in facts]
        self.timechart.draw(durations, facts[0]["date"], facts[-1]["date"])


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
9am you seem to be an early bird.") % ("<b>%d</b>" % early_percent)
        elif late_percent >= 20:
            summary += "\n\n" + _("With %s percent of all facts starting after \
11pm you seem to be a night owl.") % ("<b>%d</b>" % late_percent)
        elif short_percent >= 20:
            summary += "\n\n" + _("With %s percent of all tasks being shorter \
than 15 minutes you seem to be a busy bee.") % ("<b>%d</b>" % short_percent)

        self.explore_summary.set_text(summary)



    def on_year_changed(self, button):
        if self.bubbling: return

        for child in button.parent.get_children():
            if child != button and child.get_active():
                self.bubbling = True
                child.set_active(False)
                self.bubbling = False

        self.stats(button.year)


    def after_fact_update(self, event):
        self.stat_facts = runtime.storage.get_facts(dt.date(1970, 1, 1), dt.date.today())
        self.stats()

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def on_window_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w
              and event_key.state & gtk.gdk.CONTROL_MASK)):
        self.close_window()

    def on_stats_window_deleted(self, widget, event):
        self.close_window()

    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            return False


if __name__ == "__main__":
    stats_viewer = Stats()
    gtk.main()
