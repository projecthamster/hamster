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

import os  # for locale
import gtk, pango

from .hamster import graphics

import time, datetime as dt
import calendar

from bisect import bisect

DAY = dt.timedelta(1)
WEEK = dt.timedelta(7)

class TimeChart(graphics.Scene):
    """this widget is kind of half finished"""

    def __init__(self):
        graphics.Scene.__init__(self)
        self.start_time, self.end_time = None, None
        self.durations = []

        self.day_start = dt.time() # ability to start day at another hour
        self.first_weekday = self.locale_first_weekday()

        self.minor_tick = None

        self.tick_totals = []

        self.connect("on-enter-frame", self.on_enter_frame)


    def draw(self, durations, start_date, end_date):
        self.durations = durations

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        # adjust to day starts and ends if we show
        if end_date - start_date < dt.timedelta(days=1):
            start_time = dt.datetime.combine(start_date, self.day_start.replace(minute=0))
            end_time = dt.datetime.combine(end_date, self.day_start.replace(minute=0)) + dt.timedelta(days = 1)

            durations_start_time, durations_end_time = start_time, end_time
            if durations:
                durations_start_time = durations[0][0]
                durations_end_time = durations[-1][0] + durations[-1][1]

            self.start_time = min([start_time, durations_start_time])
            self.end_time = max([end_time, durations_end_time])

        else:
            start_time = dt.datetime.combine(start_date, dt.time())
            end_time = dt.datetime.combine(end_date, dt.time(23, 59))

            durations_start_time, durations_end_time = start_time, end_time
            if durations:
                durations_start_time = dt.datetime.combine(durations[0][0], dt.time())
                durations_end_time = dt.datetime.combine(durations[-1][0], dt.time())

                if isinstance(durations[0][0], dt.datetime):
                    durations_start_time = durations_start_time - dt.timedelta(1 if durations[0][0].time() < self.day_start else 0)
                    durations_end_time = durations_end_time - dt.timedelta(1 if durations[-1][0].time() < self.day_start else 0)

            self.start_time = min([start_time, durations_start_time])
            self.end_time = max([end_time, durations_end_time])

        days = (end_date - start_date).days


        # determine fraction and do addittional start time move
        if days > 125: # about 4 month -> show per month
            self.minor_tick = dt.timedelta(days = 30) #this is approximate and will be replaced by exact days in month
            # make sure we start on first day of month
            self.start_time = self.start_time - dt.timedelta(self.start_time.day - 1)

        elif days > 40: # bit more than month -> show per week
            self.minor_tick = WEEK
            # make sure we start week on first day
            #set to monday
            start_time = self.start_time - dt.timedelta(self.start_time.weekday() + 1)
            # look if we need to start on sunday or monday
            start_time = start_time + dt.timedelta(self.first_weekday)
            if self.start_time - start_time == WEEK:
                start_time += WEEK
            self.start_time = start_time
        elif days >= 1: # more than two days -> show per day
            self.minor_tick = DAY
        else: # show per hour
            self.minor_tick = dt.timedelta(seconds = 60 * 60)

        self.count_hours()

        self.redraw()


    def on_enter_frame(self, scene, context):
        if not self.start_time or not self.end_time:
            return

        g = graphics.Graphics(context)

        # figure out colors
        bg_color = self.get_style().bg[gtk.STATE_NORMAL].to_string()
        if g.colors.is_light(bg_color):
            bar_color = g.colors.darker(bg_color,  30)
            tick_color = g.colors.darker(bg_color,  50)
        else:
            bar_color = g.colors.darker(bg_color,  -30)
            tick_color = g.colors.darker(bg_color,  -50)

        # now for the text - we want reduced contrast for relaxed visuals
        fg_color = self.get_style().fg[gtk.STATE_NORMAL].to_string()
        if g.colors.is_light(fg_color):
            label_color = g.colors.darker(fg_color,  70)
        else:
            label_color = g.colors.darker(fg_color,  -70)


        g.set_line_style(width=1)

        # major ticks
        if self.end_time - self.start_time < dt.timedelta(days=1):  # about the same day
            major_step = dt.timedelta(seconds = 60 * 60)
        else:
            major_step = dt.timedelta(days=1)


        def first_weekday(date):
            return (date.weekday() + 1 - self.first_weekday) % 7 == 0

        # count ticks so we can correctly calculate the average bar width
        ticks = []
        for i, (current_time, total) in enumerate(self.tick_totals):
            # move the x bit further when ticks kick in
            if (major_step < DAY and current_time.time() == dt.time(0,0)) \
               or (self.minor_tick == DAY and first_weekday(current_time)) \
               or (self.minor_tick <= WEEK and current_time.day == 1) \
               or (current_time.timetuple().tm_yday == 1):
                ticks.append(current_time)


        # calculate position of each bar
        # essentially we care more about the exact 1px gap between bars than about the bar width
        # so after each iteration, we adjust the bar width
        exes = {}

        x = 0
        bar_width = (float(self.width) - len(ticks) * 2)  / len(self.tick_totals)
        remaining_ticks = len(ticks)
        for i, (current_time, total) in enumerate(self.tick_totals):
            # move the x bit further when ticks kick in
            if current_time in ticks:
                x += 2
                remaining_ticks -= 1

            exes[current_time] = (x, int(bar_width)) #saving those as getting pixel precision is not an exact science

            x = int(x + bar_width)
            bar_width = (self.width - x - remaining_ticks * 2) / float(max(len(self.tick_totals) - i - 1, 1))



        def line(x, color):
            g.move_to(round(x) + 0.5, 0)
            g.set_color(color)
            g.line_to(round(x) + 0.5, self.height)
            g.stroke()

        def somewhere_in_middle(time, color):
            # draws line somewhere in middle of the minor tick
            left_index = exes.keys()[bisect(exes.keys(), time) - 1]
            #should yield something between 0 and 1
            adjustment = self.duration_minutes(time - left_index) / float(self.duration_minutes(self.minor_tick))
            x, width = exes[left_index]
            line(x + round(width * adjustment) - 1, color)


        # mark tick lines
        current_time = self.start_time + major_step
        while current_time < self.end_time:
            if current_time in ticks:
                line(exes[current_time][0] - 2, tick_color)
            else:
                if self.minor_tick <= WEEK and current_time.day == 1:  # month change
                    somewhere_in_middle(current_time, tick_color)
                # year change
                elif current_time.timetuple().tm_yday == 1: # year change
                    somewhere_in_middle(current_time, tick_color)

            current_time += major_step



        # the bars
        for current_time, total in self.tick_totals:
            bar_size = max(round(self.height * total * 0.8), 1)
            x, bar_width = exes[current_time]

            g.set_color(bar_color)

            # rounded corners
            g.rectangle(x, self.height - bar_size, bar_width - 1, bar_size, 3)

            # straighten out bottom rounded corners
            g.rectangle(x, self.height - min(bar_size, 2), bar_width - 1, min(bar_size, 2))

            g.fill()


        # tick label format
        if self.minor_tick >= dt.timedelta(days = 28): # month
            step_format = "%b"

        elif self.minor_tick == WEEK: # week
            step_format = "%b %d"
        elif self.minor_tick == DAY: # day
            if (self.end_time - self.start_time) > dt.timedelta(10):
                step_format = "%b %d"
            else:
                step_format = "%a"
        else:
            step_format = "%H<small><sup>%M</sup></small>"


        # tick labels
        # TODO - should handle the layout business in graphics
        layout = context.create_layout()
        default_font = pango.FontDescription(gtk.Style().font_desc.to_string())
        default_font.set_size(8 * pango.SCALE)
        layout.set_font_description(default_font)

        for current_time, total in self.tick_totals:
            # if we are on the day level, show label only on week start
            if (self.end_time - self.start_time) > dt.timedelta(10) \
               and self.minor_tick == DAY and first_weekday(current_time) == False:
                continue

            x, bar_width = exes[current_time]

            g.set_color(label_color)
            layout.set_width(int((self.width - x) * pango.SCALE))
            layout.set_markup(current_time.strftime(step_format))
            g.move_to(x + 2, 0)
            context.show_layout(layout)


    def count_hours(self):
        #go through facts and make array of time used by our fraction
        fractions = []

        current_time = self.start_time

        minor_tick = self.minor_tick
        while current_time <= self.end_time:
            # if minor tick is month, the starting date will have been
            # already adjusted to the first
            # now we have to make sure to move month by month
            if self.minor_tick >= dt.timedelta(days=28):
                minor_tick = dt.timedelta(calendar.monthrange(current_time.year, current_time.month)[1]) # days in month

            fractions.append(current_time)
            current_time += minor_tick

        hours = [0] * len(fractions)

        tick_minutes = float(self.duration_minutes(self.minor_tick))

        for start_time, duration in self.durations:
            if isinstance(duration, dt.timedelta):
                if self.minor_tick < dt.timedelta(1):
                    end_time = start_time + duration

                    # find in which fraction the fact starts and
                    # add duration up to the border of tick to that fraction
                    # then move cursor to the start of next fraction
                    first_index = bisect(fractions, start_time) - 1
                    step_time = fractions[first_index]
                    first_end = min(end_time, step_time + self.minor_tick)
                    first_tick = self.duration_minutes(first_end - start_time) / tick_minutes

                    hours[first_index] += first_tick
                    step_time = step_time + self.minor_tick

                    # now go through ticks until we reach end of the time
                    while step_time < end_time:
                        index = bisect(fractions, step_time) - 1
                        interval = min([1, self.duration_minutes(end_time - step_time) / tick_minutes])
                        hours[index] += interval

                        step_time += self.minor_tick
                else:

                    duration_date = start_time.date() - dt.timedelta(1 if start_time.time() < self.day_start else 0)
                    hour_index = bisect(fractions, dt.datetime.combine(duration_date, dt.time())) - 1
                    hours[hour_index] += self.duration_minutes(duration)
            else:
                if isinstance(start_time, dt.datetime):
                    duration_date = start_time.date() - dt.timedelta(1 if start_time.time() < self.day_start else 0)
                else:
                    duration_date = start_time

                hour_index = bisect(fractions, dt.datetime.combine(duration_date, dt.time())) - 1
                hours[hour_index] += duration


        # now normalize
        max_hour = max(hours)
        hours = [hour / float(max_hour or 1) for hour in hours]

        self.tick_totals = zip(fractions, hours)


    def duration_minutes(self, duration):
        """returns minutes from duration, otherwise we keep bashing in same math"""
        return duration.seconds / 60 + duration.days * 24 * 60

    def locale_first_weekday(self):
        """figure if week starts on monday or sunday"""
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
            print("WARNING - Failed to get first weekday from locale")

        return first_weekday
