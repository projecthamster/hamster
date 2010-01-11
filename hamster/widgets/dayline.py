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

from .hamster import stuff
from .hamster import graphics

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
        self.range_start_int = None #same date just expressed as integer so we can interpolate it  (a temporar hack)
        
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
        
        start_time_int = int(time.mktime(start_time.timetuple()))
        
        if self.range_start:
            self.range_start = start_time
            self.scroll_to_range_start()
        else:
            self.range_start = start_time
            self.range_start_int = start_time_int


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
        return dt.datetime.fromtimestamp(self.range_start_int) + dt.timedelta(minutes = minutes) 
    

        
    def draw_cursor(self, area, event):
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x + self.graph_x
            y = event.y + self.graph_y
            state = event.state

        mouse_down = state & gtk.gdk.BUTTON1_MASK
        
        highlight_start = self.highlight_start + self.graph_x
        highlight_end = self.highlight_end + self.graph_x
            
        if highlight_start != None:
            start_drag = 10 > (highlight_start - x) > -1

            end_drag = 10 > (x - highlight_end) > -1

            if start_drag and end_drag:
                start_drag = abs(x - highlight_start) < abs(x - highlight_end)

            in_between = highlight_start <= x <= highlight_end
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
                    self.drag_start = x - self.highlight_start + self.graph_x
                elif scale:
                    self.move_type = "scale_drag"
                    self.drag_start_time = dt.datetime.fromtimestamp(self.range_start_int)

            
            if mouse_down and self.drag_start:
                start, end = 0, 0
                if self.move_type and self.move_type != "scale_drag":
                    if self.move_type == "start":
                        if 0 <= x <= self.width:
                            start = x - self.graph_x
                            end = self.highlight_end
                    elif self.move_type == "end":
                        if 0 <= x <= self.width:
                            start = self.highlight_start
                            end = x - self.graph_x
                    elif self.move_type == "move":
                        width = self.highlight_end - self.highlight_start
                        start = x - self.drag_start + self.graph_x
                        
                        end = start + width
    
                    if end - start > 1:
                        self.highlight = (self.get_time(start), self.get_time(end))
                        self.redraw_canvas()

                    self.__call_parent_time_changed()
                else:
                    self.range_start = self.drag_start_time + dt.timedelta(minutes = self.get_value_at_pos(self.drag_start) - self.get_value_at_pos(x))
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
            delta = (date - dt.datetime.fromtimestamp(self.range_start_int))
            return delta.days * 24 * 60 + delta.seconds / 60

    def scroll_to_range_start(self):
        self.tweener.killTweensOf(self)
        self.animate(self, {"range_start_int": int(time.mktime(self.range_start.timetuple())),
                            "tweenType": graphics.Easing.Expo.easeOut,
                            "tweenTime": 0.4})
        
    def on_expose(self):
        # check if maybe we are approaching day boundaries and should ask for
        # more data!
        now = dt.datetime.fromtimestamp(self.range_start_int)
        if self.on_more_data:
            date_plus = (now + dt.timedelta(hours = 12 + 2*4 + 1)).date()
            date_minus = (now - dt.timedelta(hours=1)).date()

            if date_minus != now.date() and date_minus not in self.days:
                self.facts += self.on_more_data(date_minus)
                self.days.append(date_minus)
            elif date_plus != now.date() and date_plus not in self.days:
                self.facts += self.on_more_data(date_plus)
                self.days.append(date_plus)


        context = self.context
        #TODO - use system colors and fonts
 
        context.set_line_width(1)

        #we will buffer 4 hours to both sides so partial labels also appear
        range_end = now + dt.timedelta(hours = 12 + 2 * 4)        
        self.graph_x = -self.width / 3 #so x moves one third out of screen
        
        pixels_in_minute = self.width / self.view_minutes

        minutes = self._minutes_from_start(range_end)


        graph_y = 4
        graph_height = self.height - 10
        graph_y2 = graph_y + graph_height

        
        # graph area
        self.fill_area(0, graph_y - 1, self.width, graph_height, (1,1,1))

        context.save()
        context.translate(self.graph_x, self.graph_y)
    
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
                start_minutes * pixels_in_minute + self.graph_x < self.width:
                    context.set_source_rgba(0.86, 0.86, 0.86, 0.5)

                    context.rectangle(round(start_minutes * pixels_in_minute),
                                      graph_y,
                                      round(end_minutes * pixels_in_minute - start_minutes * pixels_in_minute),
                                      graph_height - 1)
                    context.fill()
                    context.stroke()

                    context.set_source_rgba(0.86, 0.86, 0.86, 1)
                    self.context.move_to(round(start_minutes * pixels_in_minute) + 0.5, graph_y)
                    self.context.line_to(round(start_minutes * pixels_in_minute) + 0.5, graph_y2)
                    self.context.move_to(round(end_minutes * pixels_in_minute) + 0.5, graph_y)
                    self.context.line_to(round(end_minutes * pixels_in_minute) + 0.5, graph_y2)
                    context.stroke()

        
        
        #time scale
        context.set_source_rgb(0, 0, 0)
        self.layout.set_width(-1)
        for i in range(minutes):
            label_time = (now + dt.timedelta(minutes=i))
            
            if label_time.minute == 0:
                context.set_source_rgb(0.8, 0.8, 0.8)
                self.context.move_to(round(i * pixels_in_minute) + 0.5, graph_y2 - 15)
                self.context.line_to(round(i * pixels_in_minute) + 0.5, graph_y2)
                context.stroke()
            elif label_time.minute % 15 == 0:
                context.set_source_rgb(0.8, 0.8, 0.8)
                self.context.move_to(round(i * pixels_in_minute) + 0.5, graph_y2 - 5)
                self.context.line_to(round(i * pixels_in_minute) + 0.5, graph_y2)
                context.stroke()
                
                
                
            if label_time.minute == 0 and label_time.hour % 2 == 0:
                if label_time.hour == 0:
                    context.set_source_rgb(0.8, 0.8, 0.8)
                    self.context.move_to(round(i * pixels_in_minute) + 0.5, graph_y)
                    self.context.line_to(round(i * pixels_in_minute) + 0.5, graph_y2)
                    label_minutes = label_time.strftime("%b %d")
                else:
                    label_minutes = label_time.strftime("%H<small><sup>%M</sup></small>")

                context.set_source_rgb(0.4, 0.4, 0.4)
                self.layout.set_markup(label_minutes)
                label_w, label_h = self.layout.get_pixel_size()
                
                context.move_to(round(i * pixels_in_minute) + 2, graph_y2 - label_h - 8)                

                context.show_layout(self.layout)
        context.stroke()
        
        #highlight rectangle
        if self.highlight:
            self.highlight_start = round(self._minutes_from_start(self.highlight[0]) * pixels_in_minute)
            self.highlight_end = round(self._minutes_from_start(self.highlight[1]) * pixels_in_minute)

        #TODO - make a proper range check here
        if self.highlight_end + self.graph_x > 0 and self.highlight_start + self.graph_x < self.width:
            rgb = colorsys.hls_to_rgb(.6, .7, .5)

            self.fill_area(self.highlight_start,
                           graph_y,
                           self.highlight_end - self.highlight_start,
                           graph_height,
                           (rgb[0], rgb[1], rgb[2], 0.5))
            context.stroke()

            context.set_source_rgb(*rgb)
            self.context.move_to(self.highlight_start + 0.5, graph_y)
            self.context.line_to(self.highlight_start + 0.5, graph_y + graph_height)
            self.context.move_to(self.highlight_end + 0.5, graph_y)
            self.context.line_to(self.highlight_end + 0.5, graph_y + graph_height)
            context.stroke()

        context.restore()            

        #and now put a frame around the whole thing
        context.set_source_rgb(0.7, 0.7, 0.7)
        context.rectangle(0, graph_y-0.5, self.width - 0.5, graph_height)
        context.stroke()
        
        if self.move_type == "move" and (self.highlight_start + self.graph_x <= 0 or self.highlight_end + self.graph_x >= self.width):
            if self.highlight_start + self.graph_x <= 0:
                self.range_start = self.range_start - dt.timedelta(minutes=30)
            if self.highlight_end + self.graph_x >= self.width:
                self.range_start = self.range_start + dt.timedelta(minutes=30)
            
            self.scroll_to_range_start()
