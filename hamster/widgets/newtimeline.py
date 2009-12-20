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
import datetime as dt
from bisect import bisect, bisect_left

class NewTimeLine(graphics.Area):
    """this widget is kind of half finished"""
    
    def __init__(self):
        graphics.Area.__init__(self)
        self.start_date, self.end_date = None, None
        self.facts = []
        self.title = ""

        
    def draw(self, facts, start_date = None, end_date = None):
        self.facts = facts    
        self.start_date = min([dt.datetime.combine(start_date, dt.time(0,0)), facts[0]["start_time"]])
        self.end_date = max([dt.datetime.combine(end_date, dt.time(0,0)), facts[-1]["start_time"] + facts[-1]["delta"]])
        
        if self.start_date > self.end_date:
            self.start_date, self.end_date = self.end_date, self.start_date

        if self.end_date.time == dt.time(0,0):
            self.end_date += dt.timedelta(days=1)

        self.set_title()
        self.redraw_canvas()

    def set_title(self):
        dates_dict = stuff.dateDict(self.start_date, "start_")
        dates_dict.update(stuff.dateDict(self.end_date, "end_"))
        
        if self.start_date.year != self.end_date.year:
            # overview label if start and end years don't match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            self.title = _(u"%(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif self.start_date.month != self.end_date.month:
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
        bar_width, time_step = self.figure_time_fraction()
        
        self.context.translate(0.5, 0.5) #move half a pixel to get sharp lines


        #go through facts and make array of time used by our fraction
        distribution = []  # TODO - think of a better name for a variable
        
        current_time = self.start_date
        while current_time <= self.end_date:
            distribution.append(current_time)
            current_time += time_step
        
        hours = [0] * len(distribution)
        
        step_minutes = float(stuff.duration_minutes(time_step))

        for fact in self.facts:
            
            first_index = bisect_left(distribution, fact["start_time"]) - 1
            
            step_time = distribution[first_index]
            first_end = min(fact["start_time"] + fact["delta"], step_time + time_step)

            interval = stuff.duration_minutes(first_end - fact["start_time"]) / step_minutes
            
            hours[first_index] += interval

            step_time = step_time + time_step
            while step_time < fact["start_time"] + fact["delta"]:
                index = bisect_left(distribution, step_time)
                
                interval = min([1, stuff.duration_minutes(fact["start_time"] + fact["delta"] - step_time) / step_minutes])
                hours[index] += interval
                
                step_time += time_step


        per_interval = dict(zip(distribution, hours))
        
        x = 1
        current_time = self.start_date
        while current_time <= self.end_date:
            bar_size = self.height * per_interval[current_time] * 0.9
            
            self.fill_area(round(x), self.height - bar_size, round(bar_width * 0.9), bar_size, "#eeeeee")
            current_time += time_step
            x += bar_width

        print time_step
        step_format = "%H:%M"
        if time_step < dt.timedelta(seconds = 60 * 60):
            step_format = "%H:%M"
        elif time_step <= dt.timedelta(seconds = 60 * 60 * 24):
            step_format = "%H:%M"
        elif time_step <= dt.timedelta(seconds = 60 * 60 * 24 * 7):
            step_format = "%d"

        x = 1
        i = 1
        current_time = self.start_date
        while current_time <= self.end_date:
            if i % 3 == 0:
                self.set_color("#aaaaaa")
                self.context.move_to(x, 30)
                self.layout.set_text(current_time.strftime(step_format))
                self.context.show_layout(self.layout)

            current_time += time_step
            x += bar_width
            i +=1

        
        self.set_color("#aaaaaa")
        self.context.move_to(1, 1)
        font = pango.FontDescription(gtk.Style().font_desc.to_string())
        font.set_size(14 * pango.SCALE)
        font.set_weight(pango.WEIGHT_BOLD)
        self.layout.set_font_description(font)

        self.layout.set_text(self.title)

        self.context.show_layout(self.layout)


    def figure_time_fraction(self):
        bar_width = 30 # preferred bar width
        bar_count = self.width / float(bar_width)
        
        minutes = stuff.duration_minutes(self.end_date - self.start_date)
        minutes_in_unit = int(minutes / bar_count)

        # now let's find closest human understandable fraction of time that we will be actually using
        fractions = [1, 5, 15, 30, # minutes
                     60, 60 * 2, 60 * 3, 60 * 4, 60 * 8, 60 * 12, # hours (1, 2, 3, 4, 8, 12)
                     60 * 24, # days
                     60 * 24 * 7, 60 * 24 * 14, # weeks (1,2)
                     60 * 24 * 30, 60 * 24 * 30 * 3, 60 * 24 * 30 * 4, # months (1, 3, 4)
                     60 * 24 * 356] # years
        
        human_step = bisect(fractions, minutes_in_unit)
        # go to the closest side
        if human_step > 0 and abs(fractions[human_step] - minutes_in_unit) > abs(fractions[human_step - 1] - minutes_in_unit):
            human_step -=1
        
        step_minutes = fractions[human_step]
        
        bar_count = minutes / step_minutes
        bar_width = self.width / float(bar_count)
        
        time_step = dt.timedelta(days = step_minutes / (60 * 24),
                                 seconds = (step_minutes % (60 * 24)) * 60)
    
        return bar_width, time_step