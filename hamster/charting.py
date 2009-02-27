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

For graph options see the Chart class and Chart.plot function

Author: toms.baugis@gmail.com
Feel free to contribute - more info at Project Hamster web page:
http://projecthamster.wordpress.com/

Example:
    # create new chart object
    chart = Chart(max_bar_width = 40) 
    
    eventBox = gtk.EventBox() # charts go into eventboxes, or windows
    place = self.get_widget("totals_by_day") #just some placeholder

    eventBox.add(chart);
    place.add(eventBox)

    #Let's imagine that we count how many apples we have gathered, by day
    data = [["Mon", 20], ["Tue", 12], ["Wed", 80],
            ["Thu", 60], ["Fri", 40], ["Sat", 0], ["Sun", 0]]
    self.day_chart.plot(data)

"""

import gtk
import gobject
import cairo, pango
import copy
import math
from sys import maxint
import datetime as dt
import time

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
    
class Integrator(object):
    """an iterator, inspired by "visualizing data" book to simplify animation"""
    def __init__(self, start_value, damping = 0.5, attraction = 0.2):
        #if we got datetime, convert it to unix time, so we operate with numbers again
        self.current_value = start_value
        if type(start_value) == dt.datetime:
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
        self.target_value = value
        if type(value) == dt.datetime:
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
        


def size_list(set, target_set):
    """turns set lenghts into target set - trim it, stretches it, but
       keeps values for cases when lengths match
    """
    set = set[:min(len(set), len(target_set))] #shrink to target
    set += target_set[len(set):] #grow to target

    #nest
    for i in range(len(set)):
        if type(set[i]) == list:
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
    

class Chart(gtk.DrawingArea):
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
        gtk.DrawingArea.__init__(self)
        self.context = None
        self.layout = None
        self.connect("expose_event", self._expose)

        self.max_bar_width     = args.get("max_bar_width", 0)
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


        #and some defaults
        self.current_max = None
        self.integrators = []
        self.moving = False


    def plot(self, keys, data, stack_keys = None):
        """Draw chart with given data"""
        self.keys, self.data, self.stack_keys = keys, data, stack_keys

        self.show()

        if not data: #if there is no data, let's just draw blank
            self._invalidate()
            return


        min, self.max_value = get_limits(data)

        if not self.current_max:
            self.current_max = Integrator(0)
        self.current_max.target(self.max_value)
        
        self._update_targets()
        
        if self.animate:
            if not self.moving: #if we are moving, then there is a timeout somewhere already
                gobject.timeout_add(1000 / self.framerate, self._interpolate)
        else:
            def finish_all(integrators):
                for i in range(len(integrators)):
                    if type(integrators[i]) == list:
                        finish_all(integrators[i])
                    else:
                        integrators[i].finish()
    
            finish_all(self.integrators)


            self._invalidate()


    def _interpolate(self):
        """Internal function to do the math, going from previous set to the
           new one, and redraw graph"""
        #this can get called before expose    
        if not self.window:
            self._invalidate()
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

        self._invalidate()
        
        return self.moving #return if there is still work to do


    def _invalidate(self):
        """Force graph redraw"""
        if self.window:    #this can get called before expose    
            alloc = self.get_allocation()
            rect = gtk.gdk.Rectangle(alloc.x, alloc.y, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)


    def _expose(self, widget, event):
        """expose is when drawing's going on, like on _invalidate"""
        self.context = widget.window.cairo_create()
        self.context.set_antialias(cairo.ANTIALIAS_NONE)

        self.context.rectangle(event.area.x, event.area.y,
                               event.area.width, event.area.height)
        self.context.clip()

        self.layout = self.context.create_layout()
        
        default_font = pango.FontDescription(gtk.Style().font_desc.to_string())
        default_font.set_size(8 * pango.SCALE)
        self.layout.set_font_description(default_font)
        
        alloc = self.get_allocation()  #x, y, width, height
        self.width, self.height = alloc[2], alloc[3]

        # fill whole area 
        if self.background:
            self.context.rectangle(0, 0, self.width, self.height)
            self.context.set_source_rgb(*self.background)
            self.context.fill()
        
        #forward to specific implementations
        self._draw()
        self.context.stroke()

        return False


    def _update_targets(self):
        # calculates new factors and then updates existing set
        max_value = float(self.max_value) or 1 # avoid division by zero
        
        self.integrators = size_list(self.integrators, self.data)

        #need function to go recursive
        def retarget(integrators, new_values):
            for i in range(len(new_values)):
                if type(new_values[i]) == list:
                    integrators[i] = retarget(integrators[i], new_values[i])
                else:
                    if isinstance(integrators[i], Integrator) == False:
                        integrators[i] = Integrator(0)

                    integrators[i].target(new_values[i] / max_value)
            
            return integrators
    
        retarget(self.integrators, self.data)
    
    def _fill_area(self, x, y, w, h, color):
        self.context.rectangle(x, y, w, h)
        self.context.set_source_rgb(*[c / 256.0 for c in color])
        self.context.fill()

    def _draw_bar(self, x, y, w, h, color = None):
        """ draws a nice bar"""
        context = self.context
        
        base_color = color or self.bar_base_color or (220, 220, 220)

        if self.bars_beveled:
            self._fill_area(x, y, w, h,
                            [b - 30 for b in base_color])

            if w > 2 and h > 2:
                self._fill_area(x + 1, y + 1, w - 2, h - 2,
                                [b + 20 for b in base_color])
    
            if w > 3 and h > 3:
                self._fill_area(x + 2, y + 2, w - 4, h - 4, base_color)
        else:
            self._fill_area(x, y, w, h, base_color)


    def _longest_label(self, labels):
        max_extent = 0
        for label in labels:
            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()
            max_extent = max(label_w + 5, max_extent)
        
        return max_extent

    def draw(self):
        print "OMG OMG, not implemented!!!"


class BarChart(Chart):
    def _draw(self):
        # graph box dimensions

        if self.show_stack_labels:
            legend_width = self.legend_width or self._longest_label(self.keys)
        elif self.show_scale:
            if self.grid_stride < 1:
                grid_stride = int(self.max_value * self.grid_stride)
            else:
                grid_stride = int(self.grid_stride)

            scale_labels = [self.value_format % i
                  for i in range(grid_stride, int(self.max_value), grid_stride)]
            legend_width = self.legend_width or self._longest_label(scale_labels)
        else:
            legend_width = self.legend_width

        if self.stack_keys and self.labels_at_end:
            graph_x = 0
            graph_width = self.width - legend_width
        else:
            graph_x = legend_width + 8 # give some space to scale labels
            graph_width = self.width - graph_x - 10

            
            

        graph_y = 0
        graph_height = self.height - 15



        self.context.set_line_width(1)
        
        if self.chart_background:
            self._fill_area(graph_x - 1, graph_y, graph_width, graph_height,
                            self.chart_background)


        self.bar_width = min(graph_width / float(len(self.keys)), self.max_bar_width)


        # keys
        prev_end = None
        set_color(self.context, dark[8]);
        self.layout.set_width(-1)

        for i in range(len(self.keys)):
            self.layout.set_text(self.keys[i])
            label_w, label_h = self.layout.get_pixel_size()

            intended_x = graph_x + (self.bar_width * i) + (self.bar_width - label_w) / 2.0
            
            if not prev_end or intended_x > prev_end:
                self.context.move_to(intended_x, graph_y + graph_height + 4)
                self.context.show_layout(self.layout)
            
                prev_end = intended_x + label_w + 10
                


        
        context = self.context
        keys, rowcount = self.keys, len(self.keys)


        max_bar_size = graph_height
        #make sure bars don't hit the ceiling
        if self.animate:
            max_bar_size = graph_height - 10


        """draw moving parts"""
        #flip the matrix vertically, so we do not have to think upside-down
        context.set_line_width(0)

        # bars
        for i in range(rowcount):
            color = 3

            bar_start = 0
            
            base_color = self.bar_base_color or (220, 220, 220)

            gap = self.bar_width * 0.05
            bar_x = graph_x + (self.bar_width * i) + gap

            for j in range(len(self.integrators[i])):
                factor = self.integrators[i][j].value

                if factor > 0:
                    bar_size = max_bar_size * factor
                    bar_start += bar_size
                    
                    self._draw_bar(bar_x,
                                   graph_height - bar_start,
                                   self.bar_width - (gap * 2),
                                   bar_size,
                                   [col - (j * 22) for col in base_color])


        #flip the matrix back, so text doesn't come upside down
        context.transform(cairo.Matrix(yy = 1, y0 = graph_height))

        
        self.layout.set_width(-1)

        #white grid and scale values
        if self.grid_stride and self.max_value:
            # if grid stride is less than 1 then we consider it to be percentage
            if self.grid_stride < 1:
                grid_stride = int(self.max_value * self.grid_stride)
            else:
                grid_stride = int(self.grid_stride)
            
            context.set_line_width(1)
            for i in range(grid_stride, int(self.max_value), grid_stride):
                y = - max_bar_size * (i / self.max_value)

                if self.show_scale:
                    self.layout.set_text(self.value_format % i)
                    label_w, label_h = self.layout.get_pixel_size()
                    context.move_to(graph_x - label_w - 8, y - label_h / 2)
                    set_color(context, medium[8])
                    context.show_layout(self.layout)

                set_color(context, (255,255,255))
                context.move_to(graph_x, y)
                context.line_to(graph_x + graph_width, y)

        context.set_line_width(1)
        #stack keys
        if self.show_stack_labels:
            self.context.set_antialias(cairo.ANTIALIAS_DEFAULT)

            #put series keys
            set_color(context, dark[8]);
            
            y = 0
            label_y = None

            # if labels are at end, then we need show them for the last bar! 
            if self.labels_at_end:
                factors = self.integrators[0]
            else:
                factors = self.integrators[-1]

            self.layout.set_ellipsize(pango.ELLIPSIZE_END)
            self.layout.set_width(graph_x * pango.SCALE)
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
                        label_x = graph_x + graph_width 
                        line_x1 = graph_x + graph_width - 1
                        line_x2 = graph_x + graph_width - 6
                    else:
                        label_x = -8
                        line_x1 = graph_x - 6
                        line_x2 = graph_x


                    context.move_to(label_x, label_y)
                    context.show_layout(self.layout)

                    if label_y != intended_position:
                        context.move_to(line_x1, label_y + label_h / 2)
                        context.line_to(line_x2, round(y + bar_size / 2))

                    
                    



class HorizontalBarChart(Chart):
    def _draw(self):
        rowcount, keys = len(self.keys), self.keys
        
        #push graph to the right, so it doesn't overlap, and add little padding aswell
        legend_width = self.legend_width or self._longest_label(keys)

        graph_x = legend_width
        graph_x += 8 #add another 8 pixes of padding
        
        graph_width = self.width - graph_x
        graph_y, graph_height = 0, self.height


        if self.chart_background:
            self._fill_area(graph_x, graph_y, graph_width, graph_height, self.chart_background)
        
        """
        # stripes for the case i decided that they are not annoying
        for i in range(0, round(self.current_max.value), 10):
            x = graph_x + (graph_width * (i / float(self.current_max.value)))
            w = (graph_width * (5 / float(self.current_max.value)))

            self.context.set_source_rgb(0.93, 0.93, 0.93)
            self.context.rectangle(x + w, graph_y, w, graph_height)
            self.context.fill()
            self.context.stroke()
            
            self.context.set_source_rgb(0.70, 0.70, 0.70)
            self.context.move_to(x, graph_y + graph_height - 2)

            self.context.show_text(str(i))
        """
    
        if not self.data:  #if we have nothing, let's go home
            return

        
        bar_width = int(graph_height / float(rowcount))
        if self.max_bar_width:
            bar_width = min(bar_width, self.max_bar_width)

        
        max_bar_size = graph_width - 15
        gap = bar_width * 0.05


        self.layout.set_alignment(pango.ALIGN_RIGHT)
        self.layout.set_ellipsize(pango.ELLIPSIZE_END)
        
        self.layout.set_width(legend_width * pango.SCALE)

        # keys
        set_color(self.context, dark[8])        
        for i in range(rowcount):
            label = keys[i]
            
            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()

            self.context.move_to(0, (bar_width * i) + (bar_width - label_h) / 2)
            self.context.show_layout(self.layout)

        
        
        self.context.set_line_width(1)
        

        
        self.context.set_line_width(0)


        # bars and labels
        self.layout.set_width(-1)

        for i in range(rowcount):
            bar_start = 0
            base_color = self.bar_base_color or (220, 220, 220)

            gap = bar_width * 0.05

            bar_y = graph_y + (bar_width * i) + gap


            for j in range(len(self.integrators[i])):
                factor = self.integrators[i][j].value

                if factor > 0:
                    bar_size = max_bar_size * factor
                    bar_height = bar_width - (gap * 2)
                    
                    self._draw_bar(graph_x + bar_start,
                                   bar_y,
                                   bar_size,
                                   bar_height,
                                   [col - (j * 22) for col in base_color])
    
                    bar_start += bar_size

            set_color(self.context, dark[8])        
            label = self.value_format % sum(self.data[i])
            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()

            vertical_padding = (bar_width + label_h) / 2.0 - label_h
            
            if  bar_start - vertical_padding < label_w:
                label_x = graph_x + bar_start + vertical_padding
            else:
                label_x = graph_x + bar_start - label_w - vertical_padding
            
            self.context.move_to(label_x, graph_y + (bar_width * i) + (bar_width - label_h) / 2.0)
            self.context.show_layout(self.layout)


