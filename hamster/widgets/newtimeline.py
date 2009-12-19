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
from bisect import bisect

class NewTimeLine(graphics.Area):
    """this widget is kind of half finished"""
    
    def __init__(self):
        graphics.Area.__init__(self)
        self.start_date, self.end_date = None, None
        self.facts = []
        self.title = ""

        
    def draw(self, facts, start_date = None, end_date = None):
        self.facts = facts    
        self.start_date = start_date or facts[0]["date"]
        self.end_date = end_date or facts[-1]["date"]
        
        if self.start_date > self.end_date:
            self.start_date, self.end_date = self.end_date, self.start_date

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
        
        self.context.translate(0.5, 0.5)        
        x = 1
        current_time = dt.datetime.combine(self.start_date, dt.time())
        while current_time <= dt.datetime.combine(self.end_date, dt.time(23, 59)):
            self.fill_area(x, 3, round(bar_width * 0.8), self.height-6, "#eeeeee")
            current_time += time_step
            x += bar_width


        print time_step
        step_format = "%H:%M"
        if time_step <= dt.timedelta(seconds = 60 * 60):
            step_format = "%M"
        elif time_step <= dt.timedelta(seconds = 60 * 60 * 24):
            step_format = "%H:%M"
        elif time_step <= dt.timedelta(seconds = 60 * 60 * 24 * 7):
            step_format = "%d"

        x = 1
        i = 1
        current_time = dt.datetime.combine(self.start_date, dt.time())
        while current_time <= dt.datetime.combine(self.end_date, dt.time(23, 59)):
            if i % 3 == 0:
                self.set_color("#aaaaaa")
                self.context.move_to(x, 10)
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
        bar_width = 10 # 10px wide bar looks about right
        bar_count = self.width / float(bar_width)
        
        minutes = stuff.duration_minutes((self.end_date - self.start_date) + dt.timedelta(days=1))
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
        bar_width = round(self.width / float(bar_count))
        
        time_step = dt.timedelta(days = step_minutes / (60 * 24),
                                 seconds = (step_minutes % (60 * 24)) * 60)
    
        return bar_width, time_step