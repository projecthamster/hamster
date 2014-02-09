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

import time
import datetime as dt

from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject
from gi.repository import PangoCairo as pangocairo

from hamster.lib import stuff, graphics, pytweener
from hamster.lib.configuration import conf


class Selection(graphics.Sprite):
    def __init__(self, start_time = None, end_time = None):
        graphics.Sprite.__init__(self, z_order = 100)
        self.start_time, self.end_time  = None, None
        self.width, self.height = None, None
        self.fill = None # will be set to proper theme color on render
        self.fixed = False

        self.start_label = graphics.Label("", 11, "#333", visible = False)
        self.end_label = graphics.Label("", 11, "#333", visible = False)
        self.duration_label = graphics.Label("", 11, "#FFF", visible = False)

        self.add_child(self.start_label, self.end_label, self.duration_label)
        self.connect("on-render", self.on_render)


    def on_render(self, sprite):
        if not self.fill: # not ready yet
            return

        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.fill(self.fill, 0.3)

        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.stroke(self.fill)


        # adjust labels
        self.start_label.visible = self.start_time is not None and self.start_time != self.end_time
        if self.start_label.visible:
            self.start_label.text = self.start_time.strftime("%H:%M")
            if self.x - self.start_label.width - 5 > 0:
                self.start_label.x = -self.start_label.width - 5
            else:
                self.start_label.x = 5

            self.start_label.y = self.height + 2

        self.end_label.visible = self.end_time is not None and self.start_time != self.end_time
        if self.end_label.visible:
            self.end_label.text = self.end_time.strftime("%H:%M")
            self.end_label.x = self.width + 5
            self.end_label.y = self.height + 2



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
    def __init__(self, start_time = None):
        graphics.Scene.__init__(self)



        day_start = conf.get("day_start_minutes")
        self.day_start = dt.time(day_start / 60, day_start % 60)

        self.view_time = start_time or dt.datetime.combine(dt.date.today(), self.day_start)

        self.scope_hours = 24


        self.fact_bars = []
        self.categories = []

        self.connect("on-enter-frame", self.on_enter_frame)

        self.plot_area = graphics.Sprite()

        self.selection = Selection()
        self.chosen_selection = Selection()

        self.plot_area.add_child(self.selection, self.chosen_selection)

        self.drag_start = None
        self.current_x = None

        self.add_child(self.plot_area)


    def plot(self, date, facts, select_start, select_end = None):
        for bar in self.fact_bars:
            self.plot_area.sprites.remove(bar)

        self.fact_bars = []
        for fact in facts:
            fact_bar = graphics.Rectangle(0, 0, fill = "#aaa", stroke="#aaa") # dimensions will depend on screen situation
            fact_bar.fact = fact

            if fact.category in self.categories:
                fact_bar.category = self.categories.index(fact.category)
            else:
                fact_bar.category = len(self.categories)
                self.categories.append(fact.category)

            self.plot_area.add_child(fact_bar)
            self.fact_bars.append(fact_bar)

        self.view_time = dt.datetime.combine(date, self.day_start)

        self.chosen_selection.start_time = select_start
        self.chosen_selection.end_time = select_end

        self.chosen_selection.width = None
        self.chosen_selection.fixed = True
        self.chosen_selection.visible = True

        self.redraw()


    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)

        self.plot_area.y = 15.5
        self.plot_area.height = self.height - 30


        vertical = min(self.plot_area.height / 5 , 7)
        minute_pixel = (self.scope_hours * 60.0 - 15) / self.width

        g.set_line_style(width=1)
        g.translate(0.5, 0.5)


        colors = {
            "normal": self._style.get_color(gtk.StateFlags.NORMAL),
            "normal_bg": self._style.get_background_color(gtk.StateFlags.NORMAL),
            "selected": self._style.get_color(gtk.StateFlags.SELECTED),
            "selected_bg": self._style.get_background_color(gtk.StateFlags.SELECTED),
        }

        bottom = self.plot_area.y + self.plot_area.height

        for bar in self.fact_bars:
            bar.y = vertical * bar.category + 5
            bar.height = vertical

            bar_start_time = bar.fact.start_time - self.view_time
            minutes = bar_start_time.seconds / 60 + bar_start_time.days * self.scope_hours  * 60

            bar.x = round(minutes / minute_pixel) + 0.5
            bar.width = round((bar.fact.delta).seconds / 60 / minute_pixel)


        if self.chosen_selection.start_time and self.chosen_selection.width is None:
            # we have time but no pixels
            minutes = round((self.chosen_selection.start_time - self.view_time).seconds / 60 / minute_pixel) + 0.5
            self.chosen_selection.x = minutes
            if self.chosen_selection.end_time:
                self.chosen_selection.width = round((self.chosen_selection.end_time - self.chosen_selection.start_time).seconds / 60 / minute_pixel)
            else:
                self.chosen_selection.width = 0
            self.chosen_selection.height = self.chosen_selection.parent.height

            # use the oportunity to set proper colors too
            self.chosen_selection.fill = colors['selected_bg']
            self.chosen_selection.duration_label.color = colors['selected']


        self.selection.visible = self._mouse_in # TODO - think harder about the mouse_out event

        self.selection.width = 0
        self.selection.height = self.selection.parent.height
        if self.mouse_x:
            start_x = max(min(self.mouse_x, self.width-1), 0) #mouse, but within screen regions

            # check for snap points
            start_x = start_x
            minutes = int(round(start_x * minute_pixel / 15)) * 15
            start_time = self.view_time + dt.timedelta(hours = minutes / 60, minutes = minutes % 60)

            self.current_x = minutes / minute_pixel


            end_time, end_x = None, None
            if self.drag_start:
                minutes = int(self.drag_start * minute_pixel)
                end_time =  self.view_time + dt.timedelta(hours = minutes / 60, minutes = minutes % 60)
                end_x = round(self.drag_start)

            if end_time and end_time < start_time:
                start_time, end_time = end_time, start_time
                start_x, end_x = end_x, start_x


            self.selection.start_time = start_time
            self.selection.end_time = end_time

            self.selection.x = start_x
            if end_time:
                self.selection.width = end_x - start_x

            self.selection.y = 0

            self.selection.fill = "#aaa" #self.get_style().bg[gtk.StateType.SELECTED].to_string()
            self.selection.duration_label.color = "#444" #self.get_style().fg[gtk.StateType.SELECTED].to_string()


        #time scale
        g.set_color("#000")

        background = "#aaa" #self.get_style().bg[gtk.StateType.NORMAL].to_string()
        text = "#444" #self.get_style().text[gtk.StateType.NORMAL].to_string()

        tick_color = g.colors.contrast(background, 80)

        layout = g.create_layout(size = 10)
        for i in range(self.scope_hours * 60):
            label_time = (self.view_time + dt.timedelta(minutes=i))

            g.set_color(tick_color)
            if label_time.minute == 0:
                g.move_to(round(i / minute_pixel), bottom - 15)
                g.line_to(round(i / minute_pixel), bottom)
                g.stroke()
            elif label_time.minute % 15 == 0:
                g.move_to(round(i / minute_pixel), bottom - 5)
                g.line_to(round(i / minute_pixel), bottom)
                g.stroke()



            if label_time.minute == 0 and label_time.hour % 4 == 0:
                if label_time.hour == 0:
                    g.move_to(round(i / minute_pixel), self.plot_area.y)
                    g.line_to(round(i / minute_pixel), bottom)
                    label_minutes = label_time.strftime("%b %d")
                else:
                    label_minutes = label_time.strftime("%H<small><sup>%M</sup></small>")

                g.set_color(text)
                layout.set_markup(label_minutes)
                label_w, label_h = layout.get_pixel_size()

                g.move_to(round(i / minute_pixel) + 2, 0)
                pangocairo.show_layout(context, layout)

        #current time
        if self.view_time < dt.datetime.now() < self.view_time + dt.timedelta(hours = self.scope_hours):
            minutes = round((dt.datetime.now() - self.view_time).seconds / 60 / minute_pixel)
            g.move_to(minutes, self.plot_area.y)
            g.line_to(minutes, bottom)
            g.stroke("#f00", 0.4)
