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

import gtk, pango

from .hamster import graphics, stuff

from .hamster.configuration import GconfStore

import datetime as dt
import calendar

from bisect import bisect

HOUR = dt.timedelta(seconds = 60*60)
DAY = dt.timedelta(1)
WEEK = dt.timedelta(7)
MONTH = dt.timedelta(30)

class TimeLine(graphics.Area):
    """this widget is kind of half finished"""
    
    def __init__(self):
        graphics.Area.__init__(self)
        self.start_time, self.end_time = None, None
        self.facts = []
        self.day_start = GconfStore().get_day_start()
        self.first_weekday = stuff.locale_first_weekday()
        
        self.minor_tick = None
        
        self.tick_totals = []

        
    def draw(self, facts, start_date, end_date):
        self.facts = facts
        
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        # for hourly representation we will operate in minutes since and until the day start
        if end_date - start_date < dt.timedelta(days=2):
            start_time = dt.datetime.combine(start_date, self.day_start.replace(minute=0))
            end_time = dt.datetime.combine(end_date, self.day_start.replace(minute=0)) + dt.timedelta(days = 1)

            fact_start_time, fact_end_time = start_time, end_time
            if facts:
                fact_start_time = facts[0]["start_time"]
                fact_end_time = facts[-1]["start_time"] + facts[-1]["delta"]
    
            self.start_time = min([start_time, fact_start_time])
            self.end_time = max([end_time, fact_end_time])

        else:
            start_time = dt.datetime.combine(start_date, dt.time())
            end_time = dt.datetime.combine(end_date, dt.time(23, 59))

            fact_start_time, fact_end_time = start_time, end_time
            if facts:
                fact_start_time = dt.datetime.combine(facts[0]["date"], dt.time())
                fact_end_time = dt.datetime.combine(facts[-1]["date"], dt.time())
    
            self.start_time = min([start_time, fact_start_time])
            self.end_time = max([end_time, fact_end_time])



        days = (self.end_time - self.start_time).days
        

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
            if self.start_time - start_time == dt.timedelta(days=7):
                start_time += dt.timedelta(days=7)
            self.start_time = start_time
        elif days > 2: # more than two days -> show per day
            self.minor_tick = dt.timedelta(days = 1)
        else: # show per hour
            self.minor_tick = dt.timedelta(seconds = 60 * 60)

        self.count_hours()
        
        self.redraw_canvas()


    def on_expose(self):
        self.context.set_line_width(1)

        self.fill_area(0, 0, self.width, self.height, "#fafafa")
        self.context.stroke()
        
        self.height = self.height - 2
        graph_x = 2
        graph_width = self.width - graph_x - 2

        if not self.facts:
            return
        
        total_minutes = stuff.duration_minutes(self.end_time - self.start_time)
        bar_width = float(graph_width) / len(self.tick_totals)


        # calculate position of each bar
        # essentially we care more about the exact 1px gap between bars than about the bar width
        # so after each iteration, we adjust the bar width
        x = graph_x
        exes = {}
        adapted_bar_width = bar_width
        for i, (current_time, total) in enumerate(self.tick_totals):
            exes[current_time] = (x, round(adapted_bar_width)) #saving those as getting pixel precision is not an exact science
            x = round(x + adapted_bar_width)
            adapted_bar_width = (self.width - x) / float(max(len(self.tick_totals) - i - 1, 1))
        


        # major ticks
        all_times = [tick[0] for tick in self.tick_totals]

        if self.end_time - self.start_time < dt.timedelta(days=3):  # about the same day
            major_step = dt.timedelta(seconds = 60 * 60)
        else:
            major_step = dt.timedelta(days=1)
        
        x = graph_x
        major_tick_step = graph_width / (total_minutes / float(stuff.duration_minutes(major_step)))
        current_time = self.start_time
        
        def line(x, color):
            self.context.move_to(round(x) + 0.5, 0)
            self.set_color(color)
            self.context.line_to(round(x) + 0.5, self.height)
            self.context.stroke()
            
        def somewhere_in_middle(time, color):
            # draws line somewhere in middle of the minor tick
            left_index = exes.keys()[bisect(exes.keys(), time) - 1]
            #should yield something between 0 and 1
            adjustment = stuff.duration_minutes(time - left_index) / float(stuff.duration_minutes(self.minor_tick))
            x, width = exes[left_index]
            line(x + round(width * adjustment) - 1, color)
        
        def first_weekday(date):
            return (date.weekday() + 1 - self.first_weekday) % 7 == 0
        
        while current_time < self.end_time:
            current_time += major_step
            x += major_tick_step
            
            if current_time >= self.end_time: # TODO - fix the loop so we do not have to break
                break
            
            if major_step < DAY:  # about the same day
                if current_time.time() == dt.time(0,0): # midnight
                    line(exes[current_time][0] - 1, "#aaaaaa")
            else:
                if self.minor_tick == DAY:  # week change
                    if first_weekday(current_time):
                        line(exes[current_time][0] - 1, "#cccccc")
    
                if self.minor_tick <= WEEK:  # month change
                    if current_time.day == 1:
                        if current_time in exes:
                            line(exes[current_time][0] - 1, "#999999")
                        else: #if we are somewhere in middle then it gets a bit more complicated
                            somewhere_in_middle(current_time, "#999999")
        
                # year change    
                if current_time.timetuple().tm_yday == 1: # year change
                    if current_time in exes:
                        line(exes[current_time][0] - 1, "#00ff00")
                    else: #if we are somewhere in middle - then just draw it
                        somewhere_in_middle(current_time, "#00ff00")



        # the bars        
        for i, (current_time, total) in enumerate(self.tick_totals):
            bar_size = max(round(self.height * total * 0.9), 1)
            x, bar_width = exes[current_time]

            self.fill_area(x, self.height - bar_size, min(bar_width - 1, self.width - x - 2), bar_size, "#E4E4E4")



        #minor tick format
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


        # ticks. we loop once again to avoid next bar overlapping previous text
        for i, (current_time, total) in enumerate(self.tick_totals):
            if (self.end_time - self.start_time) > dt.timedelta(10) \
               and self.minor_tick == DAY and first_weekday(current_time) == False:
                continue
            
            x, bar_width = exes[current_time]

            self.set_color("#aaaaaa")
            self.layout.set_width(int((self.width - x) * pango.SCALE))
            self.layout.set_markup(current_time.strftime(step_format))
            w, h = self.layout.get_pixel_size()
            
            self.context.move_to(x + 2, self.height - h - 2)
            self.context.show_layout(self.layout)

        
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
        
        tick_minutes = float(stuff.duration_minutes(self.minor_tick))
        
        for fact in self.facts:
            if self.minor_tick < dt.timedelta(1):
                end_time = fact["start_time"] + fact["delta"] # the thing about ongoing task - it has no end time
                
                # find in which fraction the fact starts and
                # add duration up to the border of tick to that fraction
                # then move cursor to the start of next fraction
                first_index = bisect(fractions, fact["start_time"]) - 1
                step_time = fractions[first_index]
                first_end = min(end_time, step_time + self.minor_tick)
                first_tick = stuff.duration_minutes(first_end - fact["start_time"]) / tick_minutes
                
                hours[first_index] += first_tick
                step_time = step_time + self.minor_tick
    
                # now go through ticks until we reach end of the time
                while step_time < end_time:
                    index = bisect(fractions, step_time) - 1
                    interval = min([1, stuff.duration_minutes(end_time - step_time) / tick_minutes])
                    hours[index] += interval
                    
                    step_time += self.minor_tick
            else:
                hour_index = bisect(fractions, dt.datetime.combine(fact["date"], dt.time())) - 1
                hours[hour_index] += stuff.duration_minutes(fact["delta"])

        # now normalize
        max_hour = max(hours)
        hours = [hour / float(max_hour or 1) for hour in hours]

        self.tick_totals = zip(fractions, hours)




