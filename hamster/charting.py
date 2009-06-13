# - coding: utf-8 -

# Copyright (C) 2008 Toms Bauģis <toms.baugis at gmail.com>

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


"""Small charting library that enables you to draw bar and
horizontal bar charts. This library is not intended for scientific graphs.
More like some visual clues to the user.

The whole thing is a bit of minefield, but it can bring pretty decent results
if you don't ask for much.

For graph options see the Chart class and Chart.plot function

Author: toms.baugis@gmail.com
Feel free to contribute - more info at Project Hamster web page:
http://projecthamster.wordpress.com/

"""

import gtk
import gobject
import cairo, pango
import copy
import math
from sys import maxint
import datetime as dt
import time
from hamster import graphics

# Tango colors
light = [(252, 233, 79), (252, 175, 62),  (233, 185, 110),
         (138, 226, 52), (114, 159, 207), (173, 127, 168), 
         (239, 41,  41), (238, 238, 236), (136, 138, 133)]

medium = [(237, 212, 0),  (245, 121, 0),   (193, 125, 17),
          (115, 210, 22), (52,  101, 164), (117, 80,  123), 
          (204, 0,   0),  (211, 215, 207), (85, 87, 83)]

dark = [(196, 160, 0), (206, 92, 0),    (143, 89, 2),
        (78, 154, 6),  (32, 74, 135),   (92, 53, 102), 
        (164, 0, 0),   (186, 189, 182), (46, 52, 54)]


def set_color(context, color, g = None, b = None):
    if g and b:
        r,g,b = color / 255.0, g / 255.0, b / 255.0
    else:
        r,g,b = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
    context.set_source_rgb(r, g, b)
    

def set_color_gdk(context, color):
    # set_color_gdk(context, self.style.fg[gtk.STATE_NORMAL]);
    r,g,b = color.red / 65536.0, color.green / 65536.0, color.blue / 65536.0
    context.set_source_rgb(r, g, b)
    
def size_list(set, target_set):
    """turns set lenghts into target set - trim it, stretches it, but
       keeps values for cases when lengths match
    """
    set = set[:min(len(set), len(target_set))] #shrink to target
    set += target_set[len(set):] #grow to target

    #nest
    for i in range(len(set)):
        if isinstance(set[i], list):
            set[i] = size_list(set[i], target_set[i])
    return set

def get_limits(set, stack_subfactors = True):
    # stack_subfactors indicates whether we should sum up nested lists
    max_value, min_value = -maxint, maxint
    for col in set:
        if type(col) in [int, float]:
            max_value = max(col, max_value)
            min_value = min(col, min_value)
        elif stack_subfactors:
            max_value = max(sum(col), max_value)
            min_value = min(sum(col), min_value)
        else:
            for row in col:
                max_value = max(row, max_value)
                min_value = max(row, min_value)

    return min_value, max_value
    

class Chart(graphics.Area):
    """Chart constructor. Optional arguments:
        self.max_bar_width     = pixels. Maximal width of bar. If not specified,
                                 bars will stretch to fill whole area
        self.legend_width      = pixels. Legend width will keep you graph
                                 from floating around.
        self.animate           = Should transitions be animated.
                                 Defaults to TRUE
        self.framerate         = Frame rate for animation. Defaults to 60

        self.background        = Tripplet-tuple of background color in RGB
        self.chart_background  = Tripplet-tuple of chart background color in RGB
        self.bar_base_color    = Tripplet-tuple of bar color in RGB
        self.bars_beveled      = Should bars be beveled. 

        self.show_scale        = Should we show scale values. See grid_stride!
        self.grid_stride       = Step of grid. If expressed in normalized range
                                 (0..1), will be treated as percentage.
                                 Otherwise will be striding through maximal value.
                                 Defaults to 0. Which is "don't draw"

        self.values_on_bars    = Should values for each bar displayed on top of
                                 it.
        self.value_format      = Format string for values. Defaults to "%s"

        self.show_stack_labels = If the labels of stack bar chart should be
                                 displayed. Defaults to False
        self.labels_at_end     = If stack bars are displayed, this allows to
                                 show them at right end of graph.
    """
    def __init__(self, **args):
        graphics.Area.__init__(self)

        self.max_bar_width     = args.get("max_bar_width", 500)
        self.legend_width      = args.get("legend_width", 0)
        self.animate           = args.get("animate", True)

        self.background        = args.get("background", None)
        self.chart_background  = args.get("chart_background", None)
        self.bar_base_color    = args.get("bar_base_color", None)

        self.grid_stride       = args.get("grid_stride", None)
        self.bars_beveled      = args.get("bars_beveled", True)
        self.values_on_bars    = args.get("values_on_bars", False)
        self.value_format      = args.get("value_format", "%s")
        self.show_scale        = args.get("show_scale", False)

        self.show_stack_labels = args.get("show_stack_labels", False)
        self.labels_at_end     = args.get("labels_at_end", False)
        self.framerate         = args.get("framerate", 60)

        # more data from left side function
        self.more_on_left      = args.get("more_on_left", None)
        self.less_on_left      = args.get("less_on_left", None)
        self.min_key_count     = args.get("min_key_count", None)


        if self.more_on_left:
            self.drag_start, self.move_type = None, None
            self.set_events(gtk.gdk.EXPOSURE_MASK
                                     | gtk.gdk.LEAVE_NOTIFY_MASK
                                     | gtk.gdk.BUTTON_PRESS_MASK
                                     | gtk.gdk.BUTTON_RELEASE_MASK
                                     | gtk.gdk.POINTER_MOTION_MASK
                                     | gtk.gdk.POINTER_MOTION_HINT_MASK)
            self.connect("button_release_event", self.on_mouse_release)
            self.connect("motion_notify_event", self.on_mouse_move)
            

        #and some defaults
        self.current_max = None
        self.integrators = []
        self.moving = False
        self.drag_x = 0
        self.before_drag_animate = None
            


    def on_mouse_release(self, area, event):
        #TODO - when mouse is released, reset graph_x to the current bar
        if not self.drag_start:
            return
        self.drag_x = 0
        self.drag_start, self.move_type = None, None
        self.animate = self.before_drag_animate
        self.redraw_canvas()


    def on_mouse_move(self, area, event):
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state

        mouse_down = state & gtk.gdk.BUTTON1_MASK
        
        if mouse_down and not self.drag_start:
            self.before_drag_animate = self.animate
            self.animate = False

            self.drag_start = x
            self.move_type = "left_side"
            
        if self.move_type == "left_side":
            #the "give me more" gesture on left side
            self.drag_x = x - self.drag_start
            if self.drag_x < 0 and len(self.keys) <= self.min_key_count:
                self.drag_x = 0

            #we are going for more, if we have dragged out previous one!
            if self.graph_x >= self.legend_width:
                self.drag_x = 0
                self.drag_start = x
                self.more_on_left()
                return
    
            if self.drag_x <= -self.legend_width and len(self.keys) > self.min_key_count:
                self.drag_x = 0
                self.drag_start = x
                self.less_on_left()
                return

            self.redraw_canvas()
        
        
    def draw_bar(self, x, y, w, h, color = None):
        """ draws a simple bar"""
        base_color = color or self.bar_base_color or (220, 220, 220)

        if self.bars_beveled:
            self.fill_area(x, y, w, h,
                            [b - 30 for b in base_color])

            if w > 2 and h > 2:
                self.fill_area(x + 1, y + 1, w - 2, h - 2,
                                [b + 20 for b in base_color])
    
            if w > 3 and h > 3:
                self.fill_area(x + 2, y + 2, w - 4, h - 4, base_color)
        else:
            self.fill_area(x, y, w, h, base_color)


    def plot(self, keys, data, stack_keys = None):
        """Draw chart with given data"""
        self.keys, self.data, self.stack_keys = keys, data, stack_keys

        self.show()

        if not data: #if there is no data, let's just draw blank
            self.redraw_canvas()
            return


        min, self.max_value = get_limits(data)

        if not self.current_max:
            self.current_max = graphics.Integrator(0)
        self.current_max.target(self.max_value)
        
        self._update_targets()
        
        if self.animate:
            if not self.moving: #if we are moving, then there is a timeout somewhere already
                gobject.timeout_add(1000 / self.framerate, self._interpolate)
        else:
            def finish_all(integrators):
                for i in range(len(integrators)):
                    if isinstance(integrators[i], list):
                        finish_all(integrators[i])
                    else:
                        integrators[i].finish()
    
            finish_all(self.integrators)
            self.current_max.finish()


            self.redraw_canvas()


    def _interpolate(self):
        """Internal function to do the math, going from previous set to the
           new one, and redraw graph"""
        #this can get called before expose    
        if not self.window:
            self.redraw_canvas()
            return False

        #ok, now we are good!
        self.current_max.update()


        def update_all(integrators):
            still_moving = False
            for z in range(len(integrators)):
                if isinstance(integrators[z], list):
                    still_moving = update_all(integrators[z]) or still_moving
                else:
                    still_moving = integrators[z].update() > 0.0001 or still_moving
            return still_moving

        self.moving = update_all(self.integrators)

        self.redraw_canvas()
        
        return self.moving #return if there is still work to do

    def _render(self):
        # fill whole area 
        if self.background:
            self.fill_area(0, 0, self.width, self.height, self.background)
        

    def _update_targets(self):
        # calculates new factors and then updates existing set
        max_value = float(self.max_value) or 1 # avoid division by zero
        
        self.integrators = size_list(self.integrators, self.data)

        #need function to go recursive
        def retarget(integrators, new_values):
            for i in range(len(new_values)):
                if isinstance(new_values[i], list):
                    integrators[i] = retarget(integrators[i], new_values[i])
                else:
                    if isinstance(integrators[i], graphics.Integrator) == False:
                        integrators[i] = graphics.Integrator(0)

                    integrators[i].target(new_values[i] / max_value)
            
            return integrators
    
        retarget(self.integrators, self.data)
    
    def draw(self):
        print "OMG OMG, not implemented!!!"


class BarChart(Chart):
    def _render(self):
        context = self.context
        Chart._render(self)
        
        # determine graph dimensions
        if self.show_stack_labels:
            legend_width = self.legend_width or self.longest_label(self.keys)
        elif self.show_scale:
            if self.grid_stride < 1:
                grid_stride = int(self.max_value * self.grid_stride)
            else:
                grid_stride = int(self.grid_stride)
            
            scale_labels = [self.value_format % i
                  for i in range(grid_stride, int(self.max_value), grid_stride)]
            self.legend_width = legend_width = self.legend_width or self.longest_label(scale_labels)
        else:
            legend_width = self.legend_width

        if self.stack_keys and self.labels_at_end:
            self.graph_x = 0
            self.graph_width = self.width - legend_width
        else:
            self.graph_x = legend_width + 8 # give some space to scale labels
            self.graph_width = self.width - self.graph_x - 10

        self.graph_y = 0
        self.graph_height = self.height - 15

        if self.chart_background:
            self.fill_area(self.graph_x, self.graph_y,
                           self.graph_width, self.graph_height,
                           self.chart_background)



        if self.more_on_left:
            #if there is more on left, clip the first one so we can preload it

            bar_width = min(self.graph_width / float(len(self.keys) - 1),
                                                                 self.max_bar_width)
            gap = bar_width * 0.05
    
            z = (1 - 1.0 / len(self.keys))
            z = z * z
            
            self.graph_x = legend_width  - bar_width + self.drag_x
            self.graph_width = self.width - self.graph_x - 10

        self.context.stroke()

        bar_width = min(self.graph_width / float(len(self.keys)),
                                                             self.max_bar_width)
        gap = bar_width * 0.05
        
        # flip hamster.graphics matrix so we don't think upside down
        self.set_value_range(y_max = 0, y_min = self.graph_height)

        # bars and keys
        max_bar_size = self.graph_height
        #make sure bars don't hit the ceiling
        if self.animate or self.before_drag_animate:
            max_bar_size = self.graph_height - 10


        prev_label_end = None
        self.layout.set_width(-1)

        for i in range(len(self.keys)):
            set_color(context, dark[8]);
            self.layout.set_text(self.keys[i])
            label_w, label_h = self.layout.get_pixel_size()

            intended_x = (bar_width * i) + (bar_width - label_w) / 2.0
            
            if not prev_label_end or intended_x > prev_label_end:
                self.move_to(intended_x, -4)
                context.show_layout(self.layout)
            
                prev_label_end = intended_x + label_w + 3
                

            bar_start = 0
            base_color = self.bar_base_color or (220, 220, 220)
            bar_x = self.graph_x + bar_width * i + gap

            if self.stack_keys:
                for j in range(len(self.integrators[i])):
                    factor = self.integrators[i][j].value
    
                    if factor > 0:
                        bar_size = max_bar_size * factor
                        bar_start += bar_size
                        
                        self.draw_bar(bar_x,
                                      self.graph_height - bar_start,
                                      bar_width - (gap * 2),
                                      bar_size,
                                      [col - (j * 22) for col in base_color])
            else:
                factor = self.integrators[i].value
                bar_size = max_bar_size * factor
                bar_start = bar_size

                self.draw_bar(bar_x,
                              self.graph_y + self.graph_height - bar_size,
                              bar_width - (gap * 2),
                              bar_size,
                              [col for col in base_color])

        #fill with white background (necessary for those dragging cases)
        if self.background:
            self.fill_area(0, 0, legend_width, self.height, self.background)

        #white grid and scale values
        self.layout.set_width(-1)
        if self.grid_stride and self.max_value:
            # if grid stride is less than 1 then we consider it to be percentage
            if self.grid_stride < 1:
                grid_stride = int(self.max_value * self.grid_stride)
            else:
                grid_stride = int(self.grid_stride)
            
            context.set_line_width(1)
            for i in range(grid_stride, int(self.max_value), grid_stride):
                y = max_bar_size * (i / self.max_value)

                if self.show_scale:
                    self.layout.set_text(self.value_format % i)
                    label_w, label_h = self.layout.get_pixel_size()
                    context.move_to(legend_width - label_w - 8,
                                    self.get_pixel(y_value=y) - label_h / 2)
                    set_color(context, medium[8])
                    context.show_layout(self.layout)

                set_color(context, (255, 255, 255))
                self.context.move_to(legend_width, self.get_pixel(y_value=y))
                self.context.line_to(self.width, self.get_pixel(y_value=y))


        #stack keys
        context.save()
        if self.show_stack_labels:
            context.set_line_width(1)
            context.set_antialias(cairo.ANTIALIAS_DEFAULT)

            #put series keys
            set_color(context, dark[8]);
            
            y = self.graph_height
            label_y = None

            # if labels are at end, then we need show them for the last bar! 
            if self.labels_at_end:
                factors = self.integrators[0]
            else:
                factors = self.integrators[-1]

            self.layout.set_ellipsize(pango.ELLIPSIZE_END)
            self.layout.set_width(self.graph_x * pango.SCALE)
            if self.labels_at_end:
                self.layout.set_alignment(pango.ALIGN_LEFT)
            else:
                self.layout.set_alignment(pango.ALIGN_RIGHT)
    
            for j in range(len(factors)):
                factor = factors[j].value
                bar_size = factor * max_bar_size
                
                if round(bar_size) > 0:
                    label = "%s" % self.stack_keys[j]
                    
                    
                    self.layout.set_text(label)
                    label_w, label_h = self.layout.get_pixel_size()
                    
                    y -= bar_size
                    intended_position = round(y + (bar_size - label_h) / 2)
                    
                    if label_y:
                        label_y = min(intended_position, label_y - label_h)
                    else:
                        label_y = intended_position
                    
                    if self.labels_at_end:
                        label_x = self.graph_x + self.graph_width 
                        line_x1 = self.graph_x + self.graph_width - 1
                        line_x2 = self.graph_x + self.graph_width - 6
                    else:
                        label_x = -8
                        line_x1 = self.graph_x - 6
                        line_x2 = self.graph_x


                    context.move_to(label_x, label_y)
                    context.show_layout(self.layout)

                    if label_y != intended_position:
                        context.move_to(line_x1, label_y + label_h / 2)
                        context.line_to(line_x2, round(y + bar_size / 2))

        context.stroke()
        context.restore()


class HorizontalBarChart(Chart):
    def _render(self):
        context = self.context
        Chart._render(self)
        rowcount, keys = len(self.keys), self.keys
        
        # push graph to the right, so it doesn't overlap
        legend_width = self.legend_width or self.longest_label(keys)

        self.graph_x = legend_width
        self.graph_x += 8 #add another 8 pixes of padding
        
        self.graph_width = self.width - self.graph_x
        self.graph_y, self.graph_height = 0, self.height


        if self.chart_background:
            self.fill_area(self.graph_x, self.graph_y, self.graph_width, self.graph_height, self.chart_background)
        

        # stripes for the case i decided that they are not annoying
        """
        for i in range(0, int(self.current_max.value), 10):
            x = self.graph_x + (self.graph_width * (i / float(self.current_max.value)))
            w = (self.graph_width * (5 / float(self.current_max.value)))

            context.set_source_rgb(0.93, 0.93, 0.93)
            context.rectangle(x + w, self.graph_y, w, self.graph_height)
            context.fill()
            context.stroke()
            
            context.set_source_rgb(0.70, 0.70, 0.70)
            context.move_to(x, self.graph_y + self.graph_height - 2)

            context.show_text(str(i))
        """

    
        if not self.data:  #if we have nothing, let's go home
            return

        
        bar_width = int(self.graph_height / float(rowcount))
        bar_width = min(bar_width, self.max_bar_width)

        
        max_bar_size = self.graph_width - 15
        gap = bar_width * 0.05


        self.layout.set_alignment(pango.ALIGN_RIGHT)
        self.layout.set_ellipsize(pango.ELLIPSIZE_END)
        

        
        context.set_line_width(0)

        # bars and labels
        self.layout.set_width(legend_width * pango.SCALE)

        for i in range(rowcount):
            self.layout.set_width(legend_width * pango.SCALE)
            set_color(context, dark[8])        
            label = keys[i]
            
            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(0, (bar_width * i) + (bar_width - label_h) / 2)
            context.show_layout(self.layout)

            base_color = self.bar_base_color or (220, 220, 220)

            gap = bar_width * 0.05

            bar_y = self.graph_y + (bar_width * i) + gap

            if self.stack_keys:
                bar_start = 0
                for j in range(len(self.integrators[i])):
                    factor = self.integrators[i][j].value
                    if factor > 0:
                        bar_size = max_bar_size * factor
                        bar_height = bar_width - (gap * 2)
                        
                        self.draw_bar(self.graph_x + bar_start,
                                      bar_y,
                                      bar_size,
                                      bar_height,
                                      [col - (j * 22) for col in base_color])
        
                        bar_start += bar_size
            else:
                factor = self.integrators[i].value
                bar_size = max_bar_size * factor
                bar_start = bar_size

                bar_height = bar_width - (gap * 2)
                
                self.draw_bar(self.graph_x,
                              bar_y,
                              bar_size,
                              bar_height,
                              [col for col in base_color])
                


            # values on bars
            if self.stack_keys:
                total_value = sum(self.data[i])
            else:
                total_value = self.data[i]
            
            set_color(context, dark[8])        
            label = self.value_format % total_value
            self.layout.set_width(-1)
            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()

            vertical_padding = (bar_width - (bar_width + label_h) / 2.0 ) / 2.0
            if  bar_start - vertical_padding < label_w:
                label_x = self.graph_x + bar_start + vertical_padding
            else:
                label_x = self.graph_x + bar_start - label_w - vertical_padding
            
            context.move_to(label_x, self.graph_y + (bar_width * i) + (bar_width - label_h) / 2.0)
            context.show_layout(self.layout)

        context.stroke()




class HorizontalDayChart(Chart):
    """Pretty much a horizontal bar chart, except for values it expects tuple
    of start and end time, and the whole thing hangs in air"""
    def plot_day(self, keys, data, start_time = None, end_time = None):
        self.keys, self.data = keys, data
        self.start_time, self.end_time = start_time, end_time
        self.show()
        self.redraw_canvas()
    
    def _render(self):
        context = self.context
        Chart._render(self)
        rowcount, keys = len(self.keys), self.keys
        
        start_hour = 0
        if self.start_time:
            start_hour = self.start_time.hour * 60 + self.start_time.minute
        end_hour = 24 * 60        
        if self.end_time:
            end_hour = self.end_time.hour * 60 + self.end_time.minute
        
        
        # push graph to the right, so it doesn't overlap
        legend_width = self.legend_width or self.longest_label(keys)

        self.graph_x = legend_width
        self.graph_x += 8 #add another 8 pixes of padding
        
        self.graph_width = self.width - self.graph_x
        
        #on the botttom leave some space for label
        self.layout.set_text("1234567890:")
        label_w, label_h = self.layout.get_pixel_size()
        
        self.graph_y, self.graph_height = 0, self.height - label_h - 4


        if self.chart_background:
            self.fill_area(self.graph_x, self.graph_y, self.graph_width, self.graph_height, self.chart_background)

        if not self.data:  #if we have nothing, let's go home
            return

        
        bar_width = int(self.graph_height / float(rowcount))
        bar_width = min(bar_width, self.max_bar_width)

        
        max_bar_size = self.graph_width - 15
        gap = bar_width * 0.05


        self.layout.set_alignment(pango.ALIGN_RIGHT)
        self.layout.set_ellipsize(pango.ELLIPSIZE_END)
        
        context.set_line_width(0)

        # bars and labels
        self.layout.set_width(legend_width * pango.SCALE)

        factor = max_bar_size / float(end_hour - start_hour)


        for i in range(rowcount):
            set_color(context, dark[8])        
            label = keys[i]
            
            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(0, (bar_width * i) + (bar_width - label_h) / 2)
            context.show_layout(self.layout)

            base_color = self.bar_base_color or (220, 220, 220)

            gap = bar_width * 0.05

            bar_y = self.graph_y + (bar_width * i) + gap

            
            bar_height = bar_width - (gap * 2)
            
            bar_x = (self.data[i][0].minute  + self.data[i][0].hour * 60 - start_hour) * factor
            bar_size = (self.data[i][1].minute  + self.data[i][1].hour * 60 - start_hour) * factor - bar_x
            
            self.draw_bar(self.graph_x + bar_x,
                          bar_y,
                          bar_size,
                          bar_height,
                          [col for col in base_color])

        #white grid and scale values
        self.layout.set_width(-1)

        context.set_line_width(1)

        for i in range(start_hour + (end_hour - start_hour) / 4, end_hour, (end_hour - start_hour) / 4):
            x = (i - start_hour) * factor

            self.layout.set_text(dt.time(i / 60, i % 60).strftime("%H:%M"))
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(self.graph_x + x - label_w / 2,
                            bar_y + bar_height + 4)
            set_color(context, medium[8])
            context.show_layout(self.layout)

            
            set_color(context, (255, 255, 255))
            self.context.move_to(self.graph_x + x, self.graph_y)
            self.context.line_to(self.graph_x + x, bar_y + bar_height)

                
        context.stroke()
