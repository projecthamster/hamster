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
import cairo, pango
import copy
import math
from sys import maxint
import datetime as dt
import time
import colorsys
import logging

import graphics


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
    

class Bar(object):
    def __init__(self, value, size = 0):
        self.value = value
        self.size = size
    
    def __repr__(self):
        return str((self.value, self.size))
        

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

        # options
        self.max_bar_width     = args.get("max_bar_width", 500)
        self.legend_width      = args.get("legend_width", 0)
        self.animation           = args.get("animate", True)

        self.background        = args.get("background", None)
        self.chart_background  = args.get("chart_background", None)
        self.bar_base_color    = args.get("bar_base_color", None)

        self.grid_stride       = args.get("grid_stride", None)
        self.values_on_bars    = args.get("values_on_bars", False)
        self.value_format      = args.get("value_format", "%s")
        self.show_scale        = args.get("show_scale", False)

        self.show_stack_labels = args.get("show_stack_labels", False)
        self.labels_at_end     = args.get("labels_at_end", False)
        self.framerate         = args.get("framerate", 60)

        # other stuff
        self.bars = []
        self.keys = []
        self.stack_keys = []
        
        self.key_colors = {} # key:color dictionary. if key's missing will grab basecolor
        self.stack_key_colors = {} # key:color dictionary. if key's missing will grab basecolor
        

        # use these to mark area where the "real" drawing is going on
        self.graph_x, self.graph_y = 0, 0
        self.graph_width, self.graph_height = None, None
        
        
    def get_bar_color(self, index):
        # returns color darkened by it's index
        # the approach reduces contrast by each step
        base_color = self.bar_base_color or (220, 220, 220)
        
        base_hls = colorsys.rgb_to_hls(*base_color)
        
        step = (base_hls[1] - 30) / 10 #will go from base down to 20 and max 22 steps
        
        return colorsys.hls_to_rgb(base_hls[0],
                                   base_hls[1] - step * index,
                                   base_hls[2])
        

    def draw_bar(self, x, y, w, h, color = None):
        """ draws a simple bar"""
        base_color = color or self.bar_base_color or (220, 220, 220)
        self.fill_area(x, y, w, h, base_color)


    def plot(self, keys, data, stack_keys = None):
        """Draw chart with given data"""
        self.keys, self.data, self.stack_keys = keys, data, stack_keys

        self.show()

        if not data: #if there is no data, let's just draw blank
            self.redraw_canvas()
            return


        min, self.max_value = get_limits(data)

        self._update_targets()

        if not self.animation:
            self.tweener.finish()

        self.redraw_canvas()


    def on_expose(self):
        # fill whole area 
        if self.background:
            self.fill_area(0, 0, self.width, self.height, self.background)
        

    def _update_targets(self):
        # calculates new factors and then updates existing set
        max_value = float(self.max_value) or 1 # avoid division by zero
        
        self.bars = size_list(self.bars, self.data)

        #need function to go recursive
        def retarget(bars, new_values):
            for i in range(len(new_values)):
                if isinstance(new_values[i], list):
                    bars[i] = retarget(bars[i], new_values[i])
                else:
                    if isinstance(bars[i], Bar) == False:
                        bars[i] = Bar(new_values[i], 0)
                    else:
                        bars[i].value = new_values[i]
                        for tween in self.tweener.getTweensAffectingObject(bars[i]):
                            self.tweener.removeTween(tween)

                    self.tweener.addTween(bars[i], size = bars[i].value / float(max_value))
            return bars
    
        retarget(self.bars, self.data)


    def longest_label(self, labels):
        """returns width of the longest label"""
        max_extent = 0
        for label in labels:
            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()
            max_extent = max(label_w + 5, max_extent)
        
        return max_extent
    
    def draw(self):
        logging.error("OMG OMG, not implemented!!!")


class BarChart(Chart):
    def on_expose(self):
        context = self.context
        Chart.on_expose(self)
        
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

        self.context.stroke()

        bar_width = min(self.graph_width / float(len(self.keys)),
                                                             self.max_bar_width)
        gap = bar_width * 0.05
        
        # bars and keys
        max_bar_size = self.graph_height
        #make sure bars don't hit the ceiling
        if self.animate or self.before_drag_animate:
            max_bar_size = self.graph_height - 10


        prev_label_end = None
        self.layout.set_width(-1)

        for i in range(len(self.keys)):
            self.set_color(graphics.Colors.aluminium[5]);
            self.layout.set_text(self.keys[i])
            label_w, label_h = self.layout.get_pixel_size()

            intended_x = (bar_width * i) + (bar_width - label_w) / 2.0 + self.graph_x
            
            if not prev_label_end or intended_x > prev_label_end:
                self.context.move_to(intended_x, self.graph_height + 4)
                context.show_layout(self.layout)
            
                prev_label_end = intended_x + label_w + 3
                

            bar_start = 0
            base_color = self.bar_base_color or (220, 220, 220)
            bar_x = round(self.graph_x + bar_width * i + gap)

            if self.stack_keys:
                for j, bar in enumerate(self.bars[i]):
                    if bar.size > 0:
                        bar_size = round(max_bar_size * bar.size)
                        bar_start += bar_size
                        
                        last_color = self.stack_key_colors.get(self.stack_keys[j],
                                                               self.get_bar_color(j))
                        self.draw_bar(bar_x,
                                      self.graph_height - bar_start,
                                      round(bar_width - (gap * 2)),
                                      bar_size,
                                      last_color)
            else:
                bar_size = round(max_bar_size * self.bars[i].size)
                bar_start = bar_size

                last_color = self.key_colors.get(self.keys[i],
                                                  base_color)
                self.draw_bar(bar_x,
                              self.graph_y + self.graph_height - bar_size,
                              round(bar_width - (gap * 2)),
                              bar_size,
                              last_color)


            if self.values_on_bars:  # it's either stack labels or values at the end for now
                if self.stack_keys:
                    total_value = sum(self.data[i])
                else:
                    total_value = self.data[i]
                
                self.layout.set_width(-1)
                self.layout.set_text(self.value_format % total_value)
                label_w, label_h = self.layout.get_pixel_size()
    

                if bar_start > label_h + 2:
                    label_y = self.graph_y + self.graph_height - bar_start + 5
                else:
                    label_y = self.graph_y + self.graph_height - bar_start - label_h + 5
                
                context.move_to(self.graph_x + (bar_width * i) + (bar_width - label_w) / 2.0, label_y)

                # we are in the bar so make sure that the font color is distinguishable
                if colorsys.rgb_to_hls(*graphics.Colors.rgb(last_color))[1] < 150:
                    self.set_color(graphics.Colors.almost_white)
                else:
                    self.set_color(graphics.Colors.aluminium[5])        

                context.show_layout(self.layout)
    
                # values on bars
                if self.stack_keys:
                    total_value = sum(self.data[i])
                else:
                    total_value = self.data[i]


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
                                    y - label_h / 2)
                    self.set_color(graphics.Colors.aluminium[4])
                    context.show_layout(self.layout)

                self.set_color((255, 255, 255))
                self.context.move_to(legend_width, y)
                self.context.line_to(self.width, y)


        #stack keys
        context.save()
        if self.show_stack_labels:
            context.set_line_width(1)
            context.set_antialias(cairo.ANTIALIAS_DEFAULT)

            #put series keys
            self.set_color(graphics.Colors.aluminium[5]);
            
            y = self.graph_height
            label_y = None

            # if labels are at end, then we need show them for the last bar! 
            if self.labels_at_end:
                factors = self.bars[0]
            else:
                factors = self.bars[-1]
            
            if isinstance(factors, Bar):
                factors = [factors]

            self.layout.set_ellipsize(pango.ELLIPSIZE_END)
            self.layout.set_width(self.graph_x * pango.SCALE)
            if self.labels_at_end:
                self.layout.set_alignment(pango.ALIGN_LEFT)
            else:
                self.layout.set_alignment(pango.ALIGN_RIGHT)
    
            for j in range(len(factors)):
                factor = factors[j].size
                bar_size = factor * max_bar_size
                
                if round(bar_size) > 0 and self.stack_keys:
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
    def on_expose(self):
        context = self.context
        Chart.on_expose(self)
        rowcount, keys = len(self.keys), self.keys
        
        # push graph to the right, so it doesn't overlap
        legend_width = self.legend_width or self.longest_label(keys)
        
        self.graph_x = legend_width
        self.graph_x += 8 #add another 8 pixes of padding
        
        self.graph_width = self.width - self.graph_x
        self.graph_y, self.graph_height = 0, self.height


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
        

        for i, label in enumerate(keys):
            self.layout.set_width(legend_width * pango.SCALE)
            self.set_color(graphics.Colors.aluminium[5])        
            
            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(0, (bar_width * i) + (bar_width - label_h) / 2)
            context.show_layout(self.layout)

            base_color = self.bar_base_color or (220, 220, 220)

            gap = bar_width * 0.05

            bar_y = round(self.graph_y + (bar_width * i) + gap)

            last_color = (255,255,255)

            if self.stack_keys:
                bar_start = 0

                for j, bar in enumerate(self.bars[i]):
                    if bar.size > 0:
                        bar_size = round(max_bar_size * bar.size)
                        bar_height = round(bar_width - (gap * 2))
                        
                        last_color = self.stack_key_colors.get(self.stack_keys[j],
                                                               self.get_bar_color(j))
                        self.draw_bar(self.graph_x + bar_start,
                                      bar_y,
                                      bar_size,
                                      bar_height,
                                      last_color)
                        bar_start += bar_size
            else:
                bar_size = round(max_bar_size * self.bars[i].size)
                bar_start = bar_size

                bar_height = round(bar_width - (gap * 2))

                last_color = self.key_colors.get(self.keys[i],
                                                 base_color)

                self.draw_bar(self.graph_x, bar_y, bar_size, bar_height,
                                                                     last_color)

            # values on bars
            if self.stack_keys:
                total_value = sum(self.data[i])
            else:
                total_value = self.data[i]
            
            self.layout.set_width(-1)
            self.layout.set_text(self.value_format % total_value)
            label_w, label_h = self.layout.get_pixel_size()

            vertical_padding = (bar_width - (bar_width + label_h) / 2.0 ) / 2.0
            if  bar_start - vertical_padding < label_w:
                label_x = self.graph_x + bar_start + vertical_padding
                self.set_color(graphics.Colors.aluminium[5])        
            else:
                # we are in the bar so make sure that the font color is distinguishable
                if colorsys.rgb_to_hls(*graphics.Colors.rgb(last_color))[1] < 150:
                    self.set_color(graphics.Colors.almost_white)
                else:
                    self.set_color(graphics.Colors.aluminium[5])        
                    
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
    
    def on_expose(self):
        context = self.context
        Chart.on_expose(self)
        rowcount, keys = len(self.keys), self.keys
        
        start_hour = 0
        if self.start_time:
            start_hour = self.start_time
        end_hour = 24 * 60        
        if self.end_time:
            end_hour = self.end_time
        
        
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


        for i, label in enumerate(keys):
            self.set_color(graphics.Colors.aluminium[5])        
            
            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(0, (bar_width * i) + (bar_width - label_h) / 2)
            context.show_layout(self.layout)

            base_color = self.bar_base_color or [220, 220, 220]

            gap = bar_width * 0.05

            bar_y = round(self.graph_y + (bar_width * i) + gap)

            
            bar_height = round(bar_width - (gap * 2))
            
            if isinstance(self.data[i], list) == False:
                self.data[i] = [self.data[i]]
            
            for row in self.data[i]:
                bar_x = round((row[0]- start_hour) * factor)
                bar_size = round((row[1] - start_hour) * factor - bar_x)
                
                self.draw_bar(self.graph_x + bar_x,
                              bar_y,
                              bar_size,
                              bar_height,
                              base_color)

        #white grid and scale values
        self.layout.set_width(-1)

        context.set_line_width(1)

        pace = ((end_hour - start_hour) / 3) / 60 * 60
        for i in range(start_hour + 60, end_hour, pace):
            x = (i - start_hour) * factor
            
            minutes = i % (24 * 60)

            self.layout.set_markup(dt.time(minutes / 60, minutes % 60).strftime("%H<small><sup>%M</sup></small>"))
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(self.graph_x + x - label_w / 2,
                            bar_y + bar_height + 4)
            self.set_color(graphics.Colors.aluminium[4])
            context.show_layout(self.layout)

            
            self.set_color((255, 255, 255))
            self.context.move_to(self.graph_x + x, self.graph_y)
            self.context.line_to(self.graph_x + x, bar_y + bar_height)

                
        context.stroke()
