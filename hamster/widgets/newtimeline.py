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

from bisect import bisect, bisect_left

class NewTimeLine(graphics.Area):
    """this widget is kind of half finished"""
    
    def __init__(self):
        graphics.Area.__init__(self)
        self.start_time, self.end_time = None, None
        self.facts = []
        self.title = ""
        self.day_start = GconfStore().get_day_start()
        self.minor_tick = None
        
        self.tick_totals = {}

        
    def draw(self, facts, start_date, end_date):
        self.facts = facts    

        self.set_title(start_date, end_date) # we will forget about all our magic manipulations for the title

        # we will operate in minutes since and until the day start
        start_time = dt.datetime.combine(start_date, self.day_start.replace(minute=0))
        end_time = dt.datetime.combine(end_date, self.day_start.replace(minute=0)) + dt.timedelta(days = 1)

        fact_start_time, fact_end_time = start_time, end_time
        if facts:
            fact_start_time = facts[0]["start_time"]
            fact_end_time = facts[-1]["start_time"] + facts[-1]["delta"]

        self.start_time = min([start_time, fact_start_time])
        self.end_time = max([end_time, fact_end_time])

        if self.start_time > self.end_time: # make sure end is after start
            self.start_time, self.end_time = self.end_time, self.start_time


        days = (self.end_time - self.start_time).days
        

        # determine fraction and do addittional start time move
        if days > 300:
            self.minor_tick = dt.timedelta(days = 30) #this is approximate and will be replaced by exact days in month
            # make sure we start on first day of month
            self.start_time = self.start_time - dt.timedelta(self.start_time.day - 1)

        elif days > 100:
            self.minor_tick = dt.timedelta(days = 7)
            # make sure we start week on first day
            #set to monday
            self.start_time = self.start_time - dt.timedelta(self.start_time.weekday() + 1)
            # look if we need to start on sunday or monday
            self.start_time = self.start_time + dt.timedelta(stuff.locale_first_weekday())
            
        elif days > 2:
            self.minor_tick = dt.timedelta(days = 1)
        else:
            self.minor_tick = dt.timedelta(seconds = 60 * 60)


        print self.start_time, self.end_time
        self.count_hours()
        


        self.redraw_canvas()

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
            end_time = fact["start_time"] + fact["delta"] # the thing about ongoing task - it has no end time
            
            # find in which fraction the fact starts and
            # add duration up to the border of tick to that fraction
            # then move cursor to the start of next fraction
            first_index = bisect_left(fractions, fact["start_time"]) - 1
            step_time = fractions[first_index]
            first_end = min(end_time, step_time + self.minor_tick)
            first_tick = stuff.duration_minutes(first_end - fact["start_time"]) / tick_minutes
            
            hours[first_index] += first_tick
            step_time = step_time + self.minor_tick

            # now go through ticks until we reach end of the time
            while step_time < end_time:
                index = bisect_left(fractions, step_time)
                interval = min([1, stuff.duration_minutes(end_time - step_time) / tick_minutes])
                hours[index] += interval
                
                step_time += self.minor_tick


        # now normalize
        max_hour = max(hours)
        hours = [hour / (max_hour or 1) for hour in hours]

        self.tick_totals = zip(fractions, hours)


    def set_title(self, start_date, end_date):
        dates_dict = stuff.dateDict(start_date, "start_")
        dates_dict.update(stuff.dateDict(end_date, "end_"))
        
        if start_date == end_date:
            # date format for overview label when only single day is visible
            # Using python datetime formatting syntax. See:
            # http://docs.python.org/library/time.html#time.strftime
            start_date_str = start_date.strftime(_("%B %d, %Y"))
            # Overview label if looking on single day
            self.title = start_date_str
        elif start_date.year != end_date.year:
            # overview label if start and end years don't match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            self.title = _(u"%(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif start_date.month != end_date.month:
            # overview label if start and end month do not match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            self.title = _(u"%(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        else:
            # overview label for interval in same month
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            self.title = _(u"%(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict


    def on_expose(self):
        self.fill_area(0, 0, self.width, self.height, "#fafafa")
        
        total_minutes = stuff.duration_minutes(self.end_time - self.start_time)
        tick_minutes = stuff.duration_minutes(self.minor_tick)
        
        bar_width = self.width / (total_minutes / float(tick_minutes))
        
        self.context.translate(0.5, 0.5) #move half a pixel to get sharp lines (hypothetically)

        # the bars        
        x = 1
        for current_time, total in self.tick_totals:
            bar_size = round(self.height * total * 0.9)
            
            self.fill_area(round(x), self.height - bar_size, round(bar_width * 0.9), bar_size, "#eeeeee")
            x += bar_width



        # major ticks
        if (self.end_time - self.start_time) < dt.timedelta(days=2):  # about the same day
            major_step = dt.timedelta(seconds = 60 * 60)
        else:
            major_step = dt.timedelta(days=1)
        
        x = 1
        major_tick_step = self.width / (total_minutes / float(stuff.duration_minutes(major_step)))
        current_time = self.start_time
        while current_time <= self.end_time:
            if (self.end_time - self.start_time) < dt.timedelta(days=2):  # about the same day
                if current_time.time() == dt.time(0,0):
                    self.fill_area(round(x), 0, 1, self.height, "#666666")

            elif self.minor_tick == dt.timedelta(days=1):  # when going day by day, tick on week, month and year change
                if current_time.weekday() == 0:
                    self.fill_area(round(x), 0, 1, self.height, "#999999")

                elif current_time.day == 1:
                    self.fill_area(round(x), 0, 1, self.height, "#666666")

                elif current_time.timetuple().tm_yday == 1:
                    self.fill_area(round(x), 0, 1, self.height, "#00FF00")
    
            elif self.minor_tick == dt.timedelta(days=7):  # when going week by week, tick on month and year change
                if current_time.day == 1:
                    self.fill_area(round(x), 0, 1, self.height, "#666666")

                elif current_time.timetuple().tm_yday == 1:
                    self.fill_area(round(x), 0, 1, self.height, "#00FF00")
    
            elif self.minor_tick >= dt.timedelta(days=28):  # when going by month, tick on year change
                if current_time.timetuple().tm_yday == 1:
                    self.fill_area(round(x), 0, 1, self.height, "#00FF00")



            current_time += major_step
            x += major_tick_step



        #minor ticks
        if self.minor_tick >= dt.timedelta(days = 28): # month
            step_format = "%b"

        elif self.minor_tick == dt.timedelta(days = 7): # week
            step_format = "%a\n%d"
        elif self.minor_tick == dt.timedelta(days = 1): # day
            step_format = "%a\n%d"
        else:        
            step_format = "%H:%M"


        x = 1
        current_time = self.start_time
        for current_time, total in self.tick_totals:
            self.set_color("#aaaaaa")
            self.layout.set_text(current_time.strftime(step_format))
            self.context.move_to(x, self.height - self.layout.get_pixel_size()[1])
            self.context.show_layout(self.layout)

            x += bar_width

        
        self.set_color("#aaaaaa")
        self.context.move_to(1, 1)
        font = pango.FontDescription(gtk.Style().font_desc.to_string())
        font.set_size(14 * pango.SCALE)
        font.set_weight(pango.WEIGHT_BOLD)
        self.layout.set_font_description(font)

        self.layout.set_text(self.title)

        self.context.show_layout(self.layout)

