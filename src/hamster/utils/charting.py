# - coding: utf-8 -

# Copyright (C) 2008-2010 Toms Bauģis <toms.baugis at gmail.com>

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

import gtk, gobject
import pango
import datetime as dt
import time
import graphics, stuff
import locale

class Bar(graphics.Sprite):
    def __init__(self, key, value, normalized, label_color):
        graphics.Sprite.__init__(self, cache_as_bitmap=True)
        self.key, self.value, self.normalized = key, value, normalized

        self.height = 0
        self.width = 20
        self.interactive = True
        self.fill = None

        self.label = graphics.Label(value, size=8, color=label_color)
        self.label_background = graphics.Rectangle(self.label.width + 4, self.label.height + 4, 4, visible=False)
        self.add_child(self.label_background)
        self.add_child(self.label)
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        # invisible rectangle for the mouse, covering whole area
        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.fill("#000", 0)

        size = round(self.width * self.normalized)

        self.graphics.rectangle(0, 0, size, self.height, 3)
        self.graphics.rectangle(0, 0, min(size, 3), self.height)
        self.graphics.fill(self.fill)

        self.label.y = (self.height - self.label.height) / 2

        horiz_offset = min(10, self.label.y * 2)

        if self.label.width < size - horiz_offset * 2:
            #if it fits in the bar
            self.label.x = size - self.label.width - horiz_offset
        else:
            self.label.x = size + 3

        self.label_background.x = self.label.x - 2
        self.label_background.y = self.label.y - 2


class Chart(graphics.Scene):
    __gsignals__ = {
        "bar-clicked": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
    }

    def __init__(self, max_bar_width = 20, legend_width = 70, value_format = "%.2f", interactive = True):
        graphics.Scene.__init__(self)

        self.selected_keys = [] # keys of selected bars

        self.bars = []
        self.labels = []
        self.data = None

        self.max_width = max_bar_width
        self.legend_width = legend_width
        self.value_format = value_format
        self.graph_interactive = interactive

        self.plot_area = graphics.Sprite(interactive = False)
        self.add_child(self.plot_area)

        self.bar_color, self.label_color = None, None

        self.connect("on-enter-frame", self.on_enter_frame)

        if self.graph_interactive:
            self.connect("on-mouse-over", self.on_mouse_over)
            self.connect("on-mouse-out", self.on_mouse_out)
            self.connect("on-click", self.on_click)

    def find_colors(self):
        bg_color = self.get_style().bg[gtk.STATE_NORMAL].to_string()
        self.bar_color = self.colors.contrast(bg_color, 30)

        # now for the text - we want reduced contrast for relaxed visuals
        fg_color = self.get_style().fg[gtk.STATE_NORMAL].to_string()
        self.label_color = self.colors.contrast(fg_color,  80)


    def on_mouse_over(self, scene, bar):
        if bar.key not in self.selected_keys:
            bar.fill = self.get_style().base[gtk.STATE_PRELIGHT].to_string()

    def on_mouse_out(self, scene, bar):
        if bar.key not in self.selected_keys:
            bar.fill = self.bar_color

    def on_click(self, scene, event, clicked_bar):
        if not clicked_bar: return
        self.emit("bar-clicked", clicked_bar.key)

    def plot(self, keys, data):
        self.data = data

        bars = dict([(bar.key, bar.normalized) for bar in self.bars])

        max_val = float(max(data or [0]))

        new_bars, new_labels = [], []
        for key, value in zip(keys, data):
            if max_val:
                normalized = value / max_val
            else:
                normalized = 0
            bar = Bar(key, locale.format(self.value_format, value), normalized, self.label_color)
            bar.interactive = self.graph_interactive

            if key in bars:
                bar.normalized = bars[key]
                self.tweener.add_tween(bar, normalized=normalized)
            new_bars.append(bar)

            label = graphics.Label(stuff.escape_pango(key), size = 8, alignment = pango.ALIGN_RIGHT)
            new_labels.append(label)


        self.plot_area.remove_child(*self.bars)
        self.remove_child(*self.labels)

        self.bars, self.labels = new_bars, new_labels
        self.add_child(*self.labels)
        self.plot_area.add_child(*self.bars)

        self.show()
        self.redraw()


    def on_enter_frame(self, scene, context):
        # adjust sizes and positions on redraw

        legend_width = self.legend_width
        if legend_width < 1: # allow fractions
            legend_width = int(self.width * legend_width)

        self.find_colors()

        self.plot_area.y = 0
        self.plot_area.height = self.height - self.plot_area.y
        self.plot_area.x = legend_width + 8
        self.plot_area.width = self.width - self.plot_area.x

        y = 0
        for i, (label, bar) in enumerate(zip(self.labels, self.bars)):
            bar_width = min(round((self.plot_area.height - y) / (len(self.bars) - i)), self.max_width)
            bar.y = y
            bar.height = bar_width
            bar.width = self.plot_area.width

            if bar.key in self.selected_keys:
                bar.fill = self.get_style().bg[gtk.STATE_SELECTED].to_string()

                if bar.normalized == 0:
                    bar.label.color = self.get_style().fg[gtk.STATE_SELECTED].to_string()
                    bar.label_background.fill = self.get_style().bg[gtk.STATE_SELECTED].to_string()
                    bar.label_background.visible = True
                else:
                    bar.label_background.visible = False
                    if bar.label.x < round(bar.width * bar.normalized):
                        bar.label.color = self.get_style().fg[gtk.STATE_SELECTED].to_string()
                    else:
                        bar.label.color = self.label_color

            if not bar.fill:
                bar.fill = self.bar_color

                bar.label.color = self.label_color
                bar.label_background.fill = None

            label.y = y + (bar_width - label.height) / 2 + self.plot_area.y

            label.width = legend_width
            if not label.color:
                label.color = self.label_color

            y += bar_width + 1




class HorizontalDayChart(graphics.Scene):
    """Pretty much a horizontal bar chart, except for values it expects tuple
    of start and end time, and the whole thing hangs in air"""
    def __init__(self, max_bar_width, legend_width):
        graphics.Scene.__init__(self)
        self.max_bar_width = max_bar_width
        self.legend_width = legend_width
        self.start_time, self.end_time = None, None
        self.connect("on-enter-frame", self.on_enter_frame)

    def plot_day(self, keys, data, start_time = None, end_time = None):
        self.keys, self.data = keys, data
        self.start_time, self.end_time = start_time, end_time
        self.show()
        self.redraw()

    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)

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

        # TODO - should handle the layout business in graphics
        self.layout = context.create_layout()
        default_font = pango.FontDescription(self.get_style().font_desc.to_string())
        default_font.set_size(8 * pango.SCALE)
        self.layout.set_font_description(default_font)


        #on the botttom leave some space for label
        self.layout.set_text("1234567890:")
        label_w, label_h = self.layout.get_pixel_size()

        self.graph_y, self.graph_height = 0, self.height - label_h - 4

        if not self.data:  #if we have nothing, let's go home
            return


        positions = {}
        y = 0
        bar_width = min(self.graph_height / float(len(self.keys)), self.max_bar_width)
        for i, key in enumerate(self.keys):
            positions[key] = (y + self.graph_y, round(bar_width - 1))

            y = y + round(bar_width)
            bar_width = min(self.max_bar_width,
                            (self.graph_height - y) / float(max(1, len(self.keys) - i - 1)))



        max_bar_size = self.graph_width - 15


        # now for the text - we want reduced contrast for relaxed visuals
        fg_color = self.get_style().fg[gtk.STATE_NORMAL].to_string()
        label_color = self.colors.contrast(fg_color,  80)

        self.layout.set_alignment(pango.ALIGN_RIGHT)
        self.layout.set_ellipsize(pango.ELLIPSIZE_END)

        # bars and labels
        self.layout.set_width(legend_width * pango.SCALE)

        factor = max_bar_size / float(end_hour - start_hour)

        # determine bar color
        bg_color = self.get_style().bg[gtk.STATE_NORMAL].to_string()
        base_color = self.colors.contrast(bg_color,  30)

        for i, label in enumerate(keys):
            g.set_color(label_color)

            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(0, positions[label][0] + (positions[label][1] - label_h) / 2)
            context.show_layout(self.layout)

            if isinstance(self.data[i], list) == False:
                self.data[i] = [self.data[i]]

            for row in self.data[i]:
                bar_x = round((row[0]- start_hour) * factor)
                bar_size = round((row[1] - start_hour) * factor - bar_x)

                g.fill_area(round(self.graph_x + bar_x),
                              positions[label][0],
                              bar_size,
                              positions[label][1],
                              base_color)

        #white grid and scale values
        self.layout.set_width(-1)

        context.set_line_width(1)

        pace = ((end_hour - start_hour) / 3) / 60 * 60
        last_position = positions[keys[-1]]


        grid_color = self.get_style().bg[gtk.STATE_NORMAL].to_string()

        for i in range(start_hour + 60, end_hour, pace):
            x = round((i - start_hour) * factor)

            minutes = i % (24 * 60)

            self.layout.set_markup(dt.time(minutes / 60, minutes % 60).strftime("%H<small><sup>%M</sup></small>"))
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(self.graph_x + x - label_w / 2,
                            last_position[0] + last_position[1] + 4)
            g.set_color(label_color)
            context.show_layout(self.layout)


            g.set_color(grid_color)
            g.move_to(round(self.graph_x + x) + 0.5, self.graph_y)
            g.line_to(round(self.graph_x + x) + 0.5,
                                 last_position[0] + last_position[1])


        context.stroke()
