# -*- coding: utf-8 -*-

# Copyright (C) 2007-2010 Toms Bauģis <toms.baugis at gmail.com>

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

import time
import datetime as dt

from .hamster import stuff
from .hamster import graphics, pytweener
from .hamster.configuration import conf


class Selection(graphics.Shape):
    def __init__(self, start_time = None, end_time = None):
        graphics.Shape.__init__(self, stroke = "#999", fill = "#999", z_order = 100)
        self.start_time, self.end_time  = None, None
        self.width, self.height = None, None
        self.fixed = False

        self.start_label = graphics.Label("", 8, "#333", visible = False)
        self.end_label = graphics.Label("", 8, "#333", visible = False)
        self.duration_label = graphics.Label("", 8, "#FFF", visible = False)

        self.add_child(self.start_label, self.end_label, self.duration_label)

    def draw_shape(self):
        self.graphics.rectangle(0, 0, self.width, self.height - self.duration_label.height - 5.5)
        self.graphics.fill(self.fill, 0.3)

        self.graphics.rectangle(0, 0, self.width, self.height - self.duration_label.height - 5.5)
        self.graphics.stroke(self.fill)


        # adjust labels
        self.start_label.visible = self.fixed == False and self.start_time is not None
        if self.start_label.visible:
            self.start_label.text = self.start_time.strftime("%H:%M")
            if self.x - self.start_label.width - 5 > 0:
                self.start_label.x = -self.start_label.width - 5
            else:
                self.start_label.x = 5

            self.start_label.y = self.height - self.start_label.height

        self.end_label.visible = self.fixed == False and self.end_time is not None
        if self.end_label.visible:
            self.end_label.text = self.end_time.strftime("%H:%M")
            self.end_label.x = self.width + 5
            self.end_label.y = self.height - self.end_label.height



            duration = self.end_time - self.start_time
            duration = int(duration.seconds / 60)
            self.duration_label.text =  "%02d:%02d" % (duration / 60, duration % 60)

            self.duration_label.visible = self.duration_label.width < self.width
            if self.duration_label.visible:
                self.duration_label.y = (self.height - self.duration_label.height) / 2
                self.duration_label.x = (self.width - self.duration_label.width) / 2
        else:
            self.duration_label.visible = False



class DayLine(graphics.Scene):
    __gsignals__ = {
        "on-time-chosen": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
    }

    def __init__(self, start_time = None):
        graphics.Scene.__init__(self)



        day_start = conf.get("day_start_minutes")
        self.day_start = dt.time(day_start / 60, day_start % 60)

        self.view_time = start_time or dt.datetime.combine(dt.date.today(), self.day_start)
        self.start_time = self.view_time - dt.timedelta(hours=12) # we will work with twice the time we will be displaying

        self.fact_bars = []
        self.categories = []

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-mouse-down", self.on_mouse_down)
        self.connect("on-mouse-up", self.on_mouse_up)
        self.connect("on-click", self.on_click)


        self.selection = Selection()
        self.chosen_selection = Selection()

        self.add_child(self.selection, self.chosen_selection)

        self.drag_start = None
        self.current_x = None
        self.snap_points = []


    def set_facts(self, facts, highlight):
        self.remove_child(*self.fact_bars)
        self.fact_bars = []
        for fact in facts:
            fact_bar = graphics.Rectangle(0, 0, fill = "#aaa", stroke="#aaa") # dimensions will depend on screen situation
            fact_bar.fact = fact

            if fact['category'] in self.categories:
                fact_bar.category = self.categories.index(fact['category'])
            else:
                fact_bar.category = len(self.categories)
                self.categories.append(fact['category'])

            self.add_child(fact_bar)
            self.fact_bars.append(fact_bar)

        self.view_time = dt.datetime.combine(highlight[0].date(), self.day_start)
        self.start_time = self.view_time - dt.timedelta(hours=12)

        if highlight:
            self.chosen_selection.start_time = highlight[0]
            self.chosen_selection.end_time = highlight[1]
            self.chosen_selection.width = None
            self.chosen_selection.fixed = True
            self.chosen_selection.visible = True

        self.redraw()


    def on_mouse_down(self, scene, event):
        self.drag_start = self.current_x
        self.chosen_selection.visible = False

    def on_mouse_up(self, scene):
        if self.drag_start:
            self.drag_start = None

            start_time = self.selection.start_time
            end_time = self.selection.end_time
            self.new_selection()
            self.emit("on-time-chosen", start_time, end_time)

    def on_click(self, scene, event, targets):
        self.drag_start = None

        start_time = self.selection.start_time
        end_time = None
        if self.fact_bars:
            times = [bar.fact['start_time'] for bar in self.fact_bars if bar.fact['start_time'] - start_time > dt.timedelta(minutes=1)]
            times.extend([bar.fact['end_time'] for bar in self.fact_bars if bar.fact['end_time'] - start_time  > dt.timedelta(minutes=1)])
            if times:
                end_time = min(times)

        self.new_selection()

        self.emit("on-time-chosen", start_time, end_time)


    def new_selection(self):
        self.sprites.remove(self.selection)
        self.selection = Selection()
        self.add_child(self.selection)
        self.redraw()

    def on_mouse_move(self, scene, event):
        if self.current_x:
            active_bar = None
            # find if we are maybe on a bar
            for bar in self.fact_bars:
                if bar.x < self.current_x < bar.x + bar.width:
                    active_bar = bar
                    break

            if active_bar:
                self.set_tooltip_text("%s - %s" % (active_bar.fact['name'], active_bar.fact['category']))
            else:
                self.set_tooltip_text("")

        self.redraw()


    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)

        vertical = 7
        minute_pixel = (24.0 * 60) / self.width

        snap_points = []

        g.set_line_style(width=1)


        bottom = self.height - self.selection.end_label.height - 5

        for bar in self.fact_bars:
            bar.y = vertical * bar.category + 5
            bar.height = vertical


            minutes = (bar.fact['start_time'] - self.view_time).seconds / 60 + (bar.fact['start_time'] - self.view_time).days * 24  * 60

            bar.x = round(minutes / minute_pixel) + 0.5
            bar.width = round((bar.fact['delta']).seconds / 60 / minute_pixel)

            snap_points.append(bar.x)
            snap_points.append(bar.x + bar.width)

        self.snap_points = snap_points


        if self.view_time < dt.datetime.now() < self.view_time + dt.timedelta(hours = 24):
            minutes = round((dt.datetime.now() - self.view_time).seconds / 60 / minute_pixel) + 0.5
            g.move_to(minutes, 0)
            g.line_to(minutes, bottom)
            g.stroke("#f00", 0.4)
            snap_points.append(minutes - 0.5)

        if self.chosen_selection.start_time and self.chosen_selection.width is None:
            # we have time but no pixels
            minutes = round((self.chosen_selection.start_time - self.view_time).seconds / 60 / minute_pixel) + 0.5
            self.chosen_selection.x = minutes - 1
            if self.chosen_selection.end_time:
                self.chosen_selection.width = round((self.chosen_selection.end_time - self.chosen_selection.start_time).seconds / 60 / minute_pixel)
            else:
                self.chosen_selection.width = 0
            self.chosen_selection.height = self.height

            # use the oportunity to set proper colors too
            self.chosen_selection.fill = self.get_style().bg[gtk.STATE_SELECTED].to_string()
            self.chosen_selection.duration_label.color = self.get_style().fg[gtk.STATE_SELECTED].to_string()


        self.selection.visible = self.mouse_x is not None

        self.selection.width = 0
        self.selection.height = self.height
        if self.mouse_x:
            start_x = max(min(self.mouse_x, self.width-1), 0) #mouse, but within screen regions

            # check for snap points
            start_x = start_x + 0.5
            minutes = int(round(start_x * minute_pixel / 15)) * 15
            if snap_points:
                delta, closest_snap = min((abs(start_x - i), i) for i in snap_points)


                if abs(closest_snap - start_x) < 5 and (not self.drag_start or self.drag_start != closest_snap):
                    start_x = closest_snap
                    minutes = int(start_x * minute_pixel)


            self.current_x = minutes / minute_pixel


            start_time = self.view_time + dt.timedelta(hours = minutes / 60, minutes = minutes % 60)

            end_time, end_x = None, None
            if self.drag_start:
                minutes = int(self.drag_start * minute_pixel)
                end_time =  self.view_time + dt.timedelta(hours = minutes / 60, minutes = minutes % 60)
                end_x = round(self.drag_start) + 0.5

            if end_time and end_time < start_time:
                start_time, end_time = end_time, start_time
                start_x, end_x = end_x, start_x


            self.selection.start_time = start_time
            self.selection.end_time = end_time

            self.selection.x = start_x
            if end_time:
                self.selection.width = end_x - start_x

            self.selection.y = 0

            self.selection.fill = self.get_style().bg[gtk.STATE_SELECTED].to_string()
            self.selection.duration_label.color = self.get_style().fg[gtk.STATE_SELECTED].to_string()



        #time scale
        g.set_color("#000")
        #self.layout.set_width(-1)

        for i in range(24*60):
            label_time = (self.view_time + dt.timedelta(minutes=i))

            if label_time.minute == 0:
                g.set_color((0.8, 0.8, 0.8))
                g.move_to(round(i / minute_pixel) + 0.5, bottom - 15)
                g.line_to(round(i / minute_pixel) + 0.5, bottom)
                g.stroke()
            elif label_time.minute % 15 == 0:
                g.set_color((0.8, 0.8, 0.8))
                g.move_to(round(i / minute_pixel) + 0.5, bottom - 5)
                g.line_to(round(i / minute_pixel) + 0.5, bottom)
                g.stroke()



            if label_time.minute == 0 and label_time.hour % 2 == 0:
                if label_time.hour == 0:
                    g.set_color((0.8, 0.8, 0.8))
                    g.move_to(round(i / minute_pixel) + 0.5, 0)
                    g.line_to(round(i / minute_pixel) + 0.5, bottom)
                    label_minutes = label_time.strftime("%b %d")
                else:
                    label_minutes = label_time.strftime("%H<small><sup>%M</sup></small>")

                g.set_color((0.4, 0.4, 0.4))
                #self.layout.set_markup(label_minutes)
                #label_w, label_h = self.layout.get_pixel_size()

                #g.move_to(round(i * pixels_in_minute) + 2, graph_y2 - label_h - 8)

                #context.show_layout(self.layout)
        g.stroke()
