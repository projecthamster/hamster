# -*- coding: utf-8 -*-

# Copyright (C) 2007-2009 Toms Bauģis <toms.baugis at gmail.com>

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

import gtk
import gobject

from hamster import stuff
from hamster import graphics

import time
import datetime as dt
import colorsys


class DayLine(graphics.Area):
    def get_value_at_pos(self, x):
        """returns mapped value at the coordinates x,y"""
        return x / float(self.width / self.view_minutes)
    
    
    #normal stuff
    def __init__(self):
        graphics.Area.__init__(self)

        self.set_events(gtk.gdk.EXPOSURE_MASK
                                 | gtk.gdk.LEAVE_NOTIFY_MASK
                                 | gtk.gdk.BUTTON_PRESS_MASK
                                 | gtk.gdk.BUTTON_RELEASE_MASK
                                 | gtk.gdk.POINTER_MOTION_MASK
                                 | gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.connect("button_release_event", self.on_button_release)
        self.connect("motion_notify_event", self.draw_cursor)
        self.highlight_start, self.highlight_end = None, None
        self.drag_start = None
        self.move_type = ""
        self.on_time_changed = None #override this with your func to get notified when user changes date
        self.on_more_data = None #supplement with more data func that accepts single date
        self.in_progress = False

        self.range_start = None
        self.in_motion = False
        self.days = []

        self.view_minutes = float(12 * 60) #how many minutes are we going to show

        # TODO - get rid of these
        # use these to mark area where the "real" drawing is going on
        self.graph_x, self.graph_y = 0, 0

    def draw(self, day_facts, highlight = None):
        """Draw chart with given data"""
        self.facts = day_facts
        if self.facts:
            self.days.append(self.facts[0]["start_time"].date())
        
        start_time = highlight[0] - dt.timedelta(minutes = highlight[0].minute) - dt.timedelta(hours = 10)
        
        if self.range_start:
            self.range_start.value = start_time
            self.scroll_to_range_start()
        else:
            self.range_start = Integrator(start_time, damping = 0.35, attraction = 0.5)

        self.highlight = highlight
        
        self.show()
        
        self.redraw_canvas()


    def on_button_release(self, area, event):
        if not self.drag_start:
            return
        
        self.drag_start, self.move_type = None, None

        if event.state & gtk.gdk.BUTTON1_MASK:
            self.__call_parent_time_changed()

    def set_in_progress(self, in_progress):
        self.in_progress = in_progress

    def __call_parent_time_changed(self):
        #now calculate back from pixels into minutes
        start_time = self.highlight[0]
        end_time = self.highlight[1]

        if self.on_time_changed:
            self.on_time_changed(start_time, end_time)
    
    def get_time(self, pixels):
        minutes = self.get_value_at_pos(x = pixels)
        return self.range_start.value + dt.timedelta(minutes = minutes) 
    
    def scroll_to_range_start(self):
        if not self.in_motion:
            self.in_motion = True
            gobject.timeout_add(1000 / 30, self.animate_scale)
        
        
    def animate_scale(self):
        moving = self.range_start.update() > 5
        
        
        # check if maybe we are approaching day boundaries and should ask for
        # more data!
        if self.on_more_data:
            now = self.range_start.value
            date_plus = (now + dt.timedelta(hours = 12 + 2*4 + 1)).date()
            date_minus = (now - dt.timedelta(hours=1)).date()

            if date_minus != now.date() and date_minus not in self.days:
                self.facts += self.on_more_data(date_minus)
                self.days.append(date_minus)
            elif date_plus != now.date() and date_plus not in self.days:
                self.facts += self.on_more_data(date_plus)
                self.days.append(date_plus)
        
        
        self.redraw_canvas()
        if moving:
            return True
        else:
            self.in_motion = False
            return False


        
    def draw_cursor(self, area, event):
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state

        mouse_down = state & gtk.gdk.BUTTON1_MASK
            
        if self.highlight_start != None:
            start_drag = 10 > (self.highlight_start - x) > -1

            end_drag = 10 > (x - self.highlight_end) > -1

            if start_drag and end_drag:
                start_drag = abs(x - self.highlight_start) < abs(x - self.highlight_end)

            in_between = self.highlight_start <= x <= self.highlight_end
            scale = True

            if self.in_progress:
                end_drag = False
                in_between = False

            if mouse_down and not self.drag_start:
                self.drag_start = x
                if start_drag:
                    self.move_type = "start"
                elif end_drag:
                    self.move_type = "end"
                elif in_between:
                    self.move_type = "move"
                    self.drag_start = x - self.highlight_start
                elif scale:
                    self.move_type = "scale_drag"
                    self.drag_start_time = self.range_start.value

            
            if mouse_down and self.drag_start:
                start, end = 0, 0
                if self.move_type and self.move_type != "scale_drag":
                    if self.move_type == "start":
                        if 0 <= x <= self.width:
                            start = x
                            end = self.highlight_end
                    elif self.move_type == "end":
                        if 0 <= x <= self.width:
                            start = self.highlight_start
                            end = x
                    elif self.move_type == "move":
                        width = self.highlight_end - self.highlight_start
                        start = x - self.drag_start
                        start = max(0, min(start, self.width))
                        
                        end = start + width
                        if end > self.width:
                            end = self.width
                            start = end - width
    
                    if end - start > 1:
                        self.highlight = (self.get_time(start), self.get_time(end))
                        self.redraw_canvas()

                    self.__call_parent_time_changed()
                else:
                    self.range_start.target(self.drag_start_time +
                                            dt.timedelta(minutes = self.get_value_at_pos(self.drag_start) - self.get_value_at_pos(x)))
                    self.scroll_to_range_start()



            if start_drag:
                area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.LEFT_SIDE))
            elif end_drag:
                area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.RIGHT_SIDE))
            elif in_between:
                area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))
            else:
                area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.ARROW))
                
        
    def _minutes_from_start(self, date):
            delta = (date - self.range_start.value)
            return delta.days * 24 * 60 + delta.seconds / 60
            
    def on_expose(self):
        context = self.context
        #TODO - use system colors and fonts
 
        context.set_line_width(1)

        #we will buffer 4 hours to both sides so partial labels also appear
        range_end = self.range_start.value + dt.timedelta(hours = 12 + 2 * 4)        
        self.graph_x = -self.width / 3 #so x moves one third out of screen
        
        pixels_in_minute = self.width / self.view_minutes

        minutes = self._minutes_from_start(range_end)


        graph_y = 4
        graph_height = self.height - 10
        graph_y2 = graph_y + graph_height

        
        # graph area
        self.fill_area(0, graph_y - 1, self.width, graph_height, (1,1,1))
    
        #bars
        for fact in self.facts:
            start_minutes = self._minutes_from_start(fact["start_time"])
            
            if fact["end_time"]:
                end_minutes = self._minutes_from_start(fact["end_time"])
            else:
                if fact["start_time"].date() > dt.date.today() - dt.timedelta(days=1):
                    end_minutes = self._minutes_from_start(dt.datetime.now())
                else:
                    end_minutes = start_minutes
            
            if end_minutes * pixels_in_minute > 0 and \
                start_minutes * pixels_in_minute < self.width:
                    context.set_source_rgba(0.86, 0.86, 0.86, 0.5)

                    context.rectangle(round(start_minutes * pixels_in_minute),
                                      graph_y,
                                      round(end_minutes * pixels_in_minute - start_minutes * pixels_in_minute),
                                      graph_height - 1)
                    context.fill()
                    context.stroke()

                    context.set_source_rgba(0.86, 0.86, 0.86, 1)
                    self.context.move_to(start_minutes * pixels_in_minute, graph_y)
                    self.context.line_to(start_minutes * pixels_in_minute, graph_y2)
                    self.context.move_to(end_minutes * pixels_in_minute, graph_y)
                    self.context.line_to(end_minutes * pixels_in_minute, graph_y2)
                    context.stroke()

        
        
        #time scale
        context.set_source_rgb(0, 0, 0)
        self.layout.set_width(-1)
        for i in range(minutes):
            label_time = (self.range_start.value + dt.timedelta(minutes=i))
            
            if label_time.minute == 0:
                context.set_source_rgb(0.8, 0.8, 0.8)
                self.context.move_to(i * pixels_in_minute, graph_y2 - 15)
                self.context.line_to(i * pixels_in_minute, graph_y2)
                context.stroke()
            elif label_time.minute % 15 == 0:
                context.set_source_rgb(0.8, 0.8, 0.8)
                self.context.move_to(i * pixels_in_minute, graph_y2 - 5)
                self.context.line_to(i * pixels_in_minute, graph_y2)
                context.stroke()
                
                
                
            if label_time.minute == 0 and label_time.hour % 2 == 0:
                if label_time.hour == 0:
                    context.set_source_rgb(0.8, 0.8, 0.8)
                    self.context.move_to(i * pixels_in_minute, graph_y)
                    self.context.line_to(i * pixels_in_minute, graph_y2)
                    label_minutes = label_time.strftime("%b %d")
                else:
                    label_minutes = label_time.strftime("%H<small><sup>%M</sup></small>")

                context.set_source_rgb(0.4, 0.4, 0.4)
                self.layout.set_markup(label_minutes)
                label_w, label_h = self.layout.get_pixel_size()
                
                context.move_to(i * pixels_in_minute + 2, graph_y2 - label_h - 8)                

                context.show_layout(self.layout)
        context.stroke()
        
        #highlight rectangle
        if self.highlight:
            self.highlight_start = round(self._minutes_from_start(self.highlight[0]) * pixels_in_minute)
            self.highlight_end = round(self._minutes_from_start(self.highlight[1]) * pixels_in_minute)

        #TODO - make a proper range check here
        if self.highlight_end > 0 and self.highlight_start < self.width:
            rgb = colorsys.hls_to_rgb(.6, .7, .5)

            self.fill_area(self.highlight_start,
                           graph_y,
                           self.highlight_end - self.highlight_start,
                           graph_height,
                           (rgb[0], rgb[1], rgb[2], 0.5))
            context.stroke()

            context.set_source_rgb(*rgb)
            self.context.move_to(self.highlight_start, graph_y)
            self.context.line_to(self.highlight_start, graph_y + graph_height)
            self.context.move_to(self.highlight_end, graph_y)
            self.context.line_to(self.highlight_end, graph_y + graph_height)
            context.stroke()

        #and now put a frame around the whole thing
        context.set_source_rgb(0.7, 0.7, 0.7)
        context.rectangle(0, graph_y-1, self.width - 1, graph_height)
        context.stroke()
        
        if self.move_type == "move" and (self.highlight_start == 0 or self.highlight_end == self.width):
            if self.highlight_start == 0:
                self.range_start.value = self.range_start.value - dt.timedelta(minutes=30)
            if self.highlight_end == self.width:
                self.range_start.value = self.range_start.value + dt.timedelta(minutes=30)
            self.scroll_to_range_start()



# TODO - should remove this and replace with standard tweening instead!
class Integrator(object):
    """an iterator, inspired by "visualizing data" book to simplify animation"""
    def __init__(self, start_value, damping = 0.5, attraction = 0.2):
        #if we got datetime, convert it to unix time, so we operate with numbers again
        self.current_value = start_value
        if isinstance(start_value, dt.datetime):
            self.current_value = int(time.mktime(start_value.timetuple()))
            
        self.value_type = type(start_value)

        self.target_value = start_value
        self.current_frame = 0

        self.targeting = False
        self.vel, self.accel, self.force = 0, 0, 0
        self.mass = 1
        self.damping = damping
        self.attraction = attraction

    def __repr__(self):
        current, target = self.current_value, self.target_value
        if self.value_type == dt.datetime:
            current = dt.datetime.fromtimestamp(current)
            target = dt.datetime.fromtimestamp(target)
        return "<Integrator %s, %s>" % (current, target)
        
    def target(self, value):
        """target next value"""
        self.targeting = True
        self.target_value = value
        if isinstance(value, dt.datetime):
            self.target_value = int(time.mktime(value.timetuple()))
        
    def update(self):
        """goes from current to target value
        if there is any action needed. returns velocity, which is synonym from
        delta. Use it to determine when animation is done (experiment to find
        value that fits you!"""

        if self.targeting:
            self.force += self.attraction * (self.target_value - self.current_value)

        self.accel = self.force / self.mass
        self.vel = (self.vel + self.accel) * self.damping
        self.current_value += self.vel    
        self.force = 0
        return abs(self.vel)

    def finish(self):
        self.current_value = self.target_value
    
    @property
    def value(self):
        if self.value_type == dt.datetime:
            return dt.datetime.fromtimestamp(self.current_value)
        else:
            return self.current_value
