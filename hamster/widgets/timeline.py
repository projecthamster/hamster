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

from hamster import graphics
import datetime as dt

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

        # TODO - get rid of these
        self.value_boundaries = None #x_min, x_max, y_min, y_max
        self.x_factor, self.y_factor = None, None        

        
    #TODO remove these obsolete functions with in-house transformations
    def set_value_range(self, x_min = None, x_max = None, y_min = None, y_max = None):
        """sets up our internal conversion matrix, because cairo one will
        scale also fonts and we need something in between!"""
        
        #store given params, we might redo the math later
        if not self.value_boundaries:
            self.value_boundaries = [x_min, x_max, y_min, y_max]
        else:
            if x_min != None:
                self.value_boundaries[0] = x_min
            if x_max != None:
                self.value_boundaries[1] = x_max
            if y_min != None:
                self.value_boundaries[2] = y_min
            if y_max != None:
                self.value_boundaries[3] = y_max 
        self.x_factor, self.y_factor = None, None
        self._get_factors()


    def move_to(self, x, y):
        """our copy of moveto that takes into account our transformations"""
        self.context.move_to(*self.get_pixel(x, y))

    def line_to(self, x, y):
        self.context.line_to(*self.get_pixel(x, y))

    def _get_factors(self):
        if not self.x_factor:
            self.x_factor = 1
            if self.value_boundaries and self.value_boundaries[0] != None and self.value_boundaries[1] != None:
                self.x_factor = float(self.width) / abs(self.value_boundaries[1] - self.value_boundaries[0])
                
        if not self.y_factor:            
            self.y_factor = 1
            if self.value_boundaries and self.value_boundaries[2] != None and self.value_boundaries[3] != None:
                self.y_factor = float(self.height) / abs(self.value_boundaries[3] - self.value_boundaries[2])

        return self.x_factor, self.y_factor        


    def get_pixel(self, x_value = None, y_value = None):
        """returns screen pixel position for value x and y. Useful to
        get and then pad something

        x = min1 + (max1 - min1) * (x / abs(max2-min2))  
            => min1 + const1 * x / const2
            => const3 = const1 / const2
            => min + x * const3
        """
        x_factor, y_factor = self._get_factors()

        if x_value != None:
            if self.value_boundaries and self.value_boundaries[0] != None:
                if self.value_boundaries[1] > self.value_boundaries[0]:
                    x_value = self.value_boundaries[0] + x_value * x_factor
                else: #case when min is larger than max (flipped)
                    x_value = self.value_boundaries[1] - x_value * x_factor
            if y_value is None:
                return x_value

        if y_value != None:
            if self.value_boundaries and self.value_boundaries[2] != None:
                if self.value_boundaries[3] > self.value_boundaries[2]:
                    y_value = self.value_boundaries[2] + y_value * y_factor
                else: #case when min is larger than max (flipped)
                    y_value = self.value_boundaries[2] - y_value * y_factor
            if x_value is None:
                return y_value + self.graph_y
            
        return x_value, y_value

    def get_value_at_pos(self, x = None, y = None):
        """returns mapped value at the coordinates x,y"""
        x_factor, y_factor = self._get_factors()
        
        if x != None:
            x = x  / x_factor
            if y is None:
                return x
        if y != None:
            y = y / y_factor
            if x is None:
                return y
        return x, y            


    # Normal stuff    
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
        
        
    def on_expose(self):
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

                        self.fill_area(round(ticker_pos * self.x_factor),
                                       round(self.height - total_length),
                                       round(self.x_factor),
                                       round(total_length),
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



