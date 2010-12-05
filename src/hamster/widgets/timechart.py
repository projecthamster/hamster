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

import os  # for locale
import gobject, gtk, pango

from ..lib import graphics, stuff

import time, datetime as dt
import calendar

from bisect import bisect

DAY = dt.timedelta(1)
WEEK = dt.timedelta(7)

class VerticalBar(graphics.Sprite):
    def __init__(self, key, format, value, normalized):
        graphics.Sprite.__init__(self)

        self.key, self.format = key, format,
        self.value, self.normalized = value, normalized

        # area dimensions - to be set externally
        self.height = 0
        self.width = 20
        self.fill = None

        self.key_label = graphics.Label(key.strftime(format), x=2, y=0, size=8, color="#000")

        self.add_child(self.key_label)
        self.show_label = True

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        # invisible rectangle for the mouse, covering whole area
        self.graphics.set_color("#000", 0)
        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.stroke()

        size = max(round(self.height * self.normalized * 0.8), 1)

        self.graphics.rectangle(0, self.height - size, self.width, size, 3)
        self.graphics.rectangle(0, self.height - min(size, 3), self.width, min(size, 3))
        self.graphics.fill(self.fill)


        if self.show_label and self.key_label not in self.sprites:
            self.add_child(self.key_label)
        elif self.show_label == False and self.key_label in self.sprites:
            self.sprites.remove(self.key_label)

class Icon(graphics.Sprite):
    def __init__(self, pixbuf, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.pixbuf = pixbuf
        self.interactive = True
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.set_source_pixbuf(self.pixbuf, 0, 0)
        self.graphics.paint()
        self.graphics.rectangle(0,0,24,24) #transparent rectangle
        self.graphics.stroke("#000", 0)


class TimeChart(graphics.Scene):
    """this widget is kind of half finished"""
    __gsignals__ = {
        'range-picked':     (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        'zoom-out-clicked': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self):
        graphics.Scene.__init__(self)
        self.start_time, self.end_time = None, None
        self.durations = []

        self.day_start = dt.time() # ability to start day at another hour
        self.first_weekday = stuff.locale_first_weekday()

        self.interactive = True

        self.minor_tick = None
        self.tick_totals = []
        self.bars = []

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-over", self.on_mouse_over)
        self.connect("on-mouse-out", self.on_mouse_out)
        self.connect("on-click", self.on_click)

        self.connect("enter_notify_event", self.on_mouse_enter)
        self.connect("leave_notify_event", self.on_mouse_leave)

        self.zoom_out_icon = Icon(self.render_icon(gtk.STOCK_ZOOM_OUT, gtk.ICON_SIZE_MENU),
                                  visible = False, z_order = 500)
        self.add_child(self.zoom_out_icon)


    def on_mouse_enter(self, scene, event):
        if (self.end_time - self.start_time) < dt.timedelta(days=356):
            self.zoom_out_icon.visible = True
        self.redraw()

    def on_mouse_leave(self, scene, event):
        self.zoom_out_icon.visible = False
        self.redraw()

    def on_mouse_over(self, scene, target):
        if isinstance(target, VerticalBar):
            bar = target
            bar.fill = self.get_style().base[gtk.STATE_PRELIGHT].to_string()
            self.set_tooltip_text(stuff.format_duration(bar.value))

            self.redraw()

    def on_mouse_out(self, scene, target):
        if isinstance(target, VerticalBar):
            bar = target
            bar.fill = self.bar_color

    def on_click(self, scene, event, target):
        if not target: return

        if target == self.zoom_out_icon:
            self.emit("zoom-out-clicked")
        elif isinstance(target, VerticalBar):
            self.emit("range-picked", target.key.date(), (target.key + self.minor_tick - dt.timedelta(days=1)).date())
        else:
            self.emit("range-picked", target.parent.key.date(), (target.parent.key + dt.timedelta(days=6)).date())


    def draw(self, durations, start_date, end_date):
        self.durations = durations

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        # adjust to day starts and ends if we show
        if end_date - start_date < dt.timedelta(days=1):
            start_time = dt.datetime.combine(start_date, self.day_start.replace(minute=0))
            end_time = dt.datetime.combine(end_date, self.day_start.replace(minute=0)) + dt.timedelta(days = 1)

            durations_start_time, durations_end_time = start_time, end_time
            if durations:
                durations_start_time = durations[0][0]
                durations_end_time = durations[-1][0] + durations[-1][1]

            self.start_time = min([start_time, durations_start_time])
            self.end_time = max([end_time, durations_end_time])

        else:
            start_time = dt.datetime.combine(start_date, dt.time())
            end_time = dt.datetime.combine(end_date, dt.time(23, 59))

            durations_start_time, durations_end_time = start_time, end_time
            if durations:
                durations_start_time = dt.datetime.combine(durations[0][0], dt.time())
                durations_end_time = dt.datetime.combine(durations[-1][0], dt.time())

                if isinstance(durations[0][0], dt.datetime):
                    durations_start_time = durations_start_time - dt.timedelta(1 if durations[0][0].time() < self.day_start else 0)
                    durations_end_time = durations_end_time - dt.timedelta(1 if durations[-1][0].time() < self.day_start else 0)

            self.start_time = min([start_time, durations_start_time])
            self.end_time = max([end_time, durations_end_time])

        days = (end_date - start_date).days


        # determine fraction and do addittional start time move
        if days > 125: # about 4 month -> show per month
            self.minor_tick = dt.timedelta(days = 30) #this is approximate and will be replaced by exact days in month
            # make sure we start on first day of month
            self.start_time = self.start_time - dt.timedelta(self.start_time.day - 1)

        elif days > 40: # bit more than month -> show per week
            self.minor_tick = WEEK
            # make sure we start week on first day
            #set to monday
            start_time = self.start_time - dt.timedelta(self.start_time.weekday() + 1)
            # look if we need to start on sunday or monday
            start_time = start_time + dt.timedelta(self.first_weekday)
            if self.start_time - start_time == WEEK:
                start_time += WEEK
            self.start_time = start_time
        elif days >= 1: # more than two days -> show per day
            self.minor_tick = DAY
        else: # show per hour
            self.minor_tick = dt.timedelta(seconds = 60 * 60)

        self.count_hours()


        self.zoom_out_icon.visible = (self.end_time - self.start_time) < dt.timedelta(days=356)

        self.redraw()

    def on_enter_frame(self, scene, context):
        if not self.start_time or not self.end_time:
            return

        g = graphics.Graphics(context)


        # figure out colors
        bg_color = self.get_style().bg[gtk.STATE_NORMAL].to_string()
        self.bar_color = g.colors.contrast(bg_color,  30)
        self.tick_color = g.colors.contrast(bg_color,  50)



        # now for the text - we want reduced contrast for relaxed visuals
        fg_color = self.get_style().fg[gtk.STATE_NORMAL].to_string()
        label_color = g.colors.contrast(fg_color,  70)


        g.set_line_style(width=1)

        # major ticks
        if self.end_time - self.start_time < dt.timedelta(days=1):  # about the same day
            major_step = dt.timedelta(seconds = 60 * 60)
        else:
            major_step = dt.timedelta(days=1)


        def first_weekday(date):
            return (date.weekday() + 1 - self.first_weekday) % 7 == 0

        # count ticks so we can correctly calculate the average bar width
        ticks = []
        for i, (current_time, total) in enumerate(self.tick_totals):
            # move the x bit further when ticks kick in
            if (major_step < DAY and current_time.time() == dt.time(0,0)) \
               or (self.minor_tick == DAY and first_weekday(current_time)) \
               or (self.minor_tick <= WEEK and current_time.day == 1) \
               or (current_time.timetuple().tm_yday == 1):
                ticks.append(current_time)


        # calculate position of each bar
        # essentially we care more about the exact 1px gap between bars than about the bar width
        # so after each iteration, we adjust the bar width
        exes = {}

        x = 0
        bar_width = round((float(self.width) - len(ticks) * 2)  / len(self.tick_totals))
        remaining_ticks = len(ticks)


        self.text_color = self.get_style().text[gtk.STATE_NORMAL].to_string()

        for i, bar in enumerate(self.bars):
            if bar.key in ticks:
                x += 2
                remaining_ticks -= 1

            bar.x = x
            bar.width = bar_width - 1
            bar.height = self.height
            bar.key_label.color = self.text_color

            if not bar.fill:
                bar.fill = self.bar_color

            bar.key_label.interactive = self.interactive and (self.end_time - self.start_time) > dt.timedelta(10) and self.minor_tick == DAY

            if (self.end_time - self.start_time) > dt.timedelta(10) \
               and self.minor_tick == DAY and first_weekday(bar.key) == False:
                bar.show_label = False
            else:
                bar.show_label = True



            exes[bar.key] = (x, int(bar_width)) #saving those as getting pixel precision is not an exact science

            x = int(x + bar_width)
            bar_width = round((self.width - x - remaining_ticks * 2) / float(max(len(self.tick_totals) - i - 1, 1)))



        def line(x, color):
            g.move_to(round(x) + 0.5, 0)
            g.line_to(round(x) + 0.5, self.height)
            g.stroke(color)

        def somewhere_in_middle(time, color):
            # draws line somewhere in middle of the minor tick
            left_index = exes.keys()[bisect(exes.keys(), time) - 1]
            #should yield something between 0 and 1
            adjustment = stuff.duration_minutes(time - left_index) / float(stuff.duration_minutes(self.minor_tick))
            x, width = exes[left_index]
            line(x + round(width * adjustment) - 1, color)


        # mark tick lines
        current_time = self.start_time + major_step
        while current_time < self.end_time:
            if current_time in ticks:
                line(exes[current_time][0] - 2, self.tick_color)
            else:
                if self.minor_tick <= WEEK and current_time.day == 1:  # month change
                    somewhere_in_middle(current_time, self.tick_color)
                # year change
                elif current_time.timetuple().tm_yday == 1: # year change
                    somewhere_in_middle(current_time, self.tick_color)

            current_time += major_step


        self.zoom_out_icon.x = self.width - 24


    def count_hours(self):
        # go through facts and make array of time used by our fraction
        fractions = []

        current_time = self.start_time

        minor_tick = self.minor_tick
        while current_time <= self.end_time:
            # if minor tick is month, the starting date will have been
            # already adjusted to the first
            # now we have to make sure to move month by month
            if self.minor_tick >= dt.timedelta(days=28):
                minor_tick = dt.timedelta(calendar.monthrange(current_time.year, current_time.month)[1]) # days in month

            fractions.append(current_time)
            current_time += minor_tick

        hours = [0] * len(fractions)

        tick_minutes = float(stuff.duration_minutes(self.minor_tick))

        for start_time, duration in self.durations:
            if isinstance(duration, dt.timedelta):
                if self.minor_tick < dt.timedelta(1):
                    end_time = start_time + duration

                    # find in which fraction the fact starts and
                    # add duration up to the border of tick to that fraction
                    # then move cursor to the start of next fraction
                    first_index = bisect(fractions, start_time) - 1
                    step_time = fractions[first_index]
                    first_end = min(end_time, step_time + self.minor_tick)
                    first_tick = stuff.duration_minutes(first_end - start_time) / tick_minutes

                    hours[first_index] += first_tick
                    step_time = step_time + self.minor_tick

                    # now go through ticks until we reach end of the time
                    while step_time < end_time:
                        index = bisect(fractions, step_time) - 1
                        interval = min([1, stuff.duration_minutes(end_time - step_time) / tick_minutes])
                        hours[index] += interval

                        step_time += self.minor_tick
                else:

                    duration_date = start_time.date() - dt.timedelta(1 if start_time.time() < self.day_start else 0)
                    hour_index = bisect(fractions, dt.datetime.combine(duration_date, dt.time())) - 1
                    hours[hour_index] += stuff.duration_minutes(duration)
            else:
                if isinstance(start_time, dt.datetime):
                    duration_date = start_time.date() - dt.timedelta(1 if start_time.time() < self.day_start else 0)
                else:
                    duration_date = start_time

                hour_index = bisect(fractions, dt.datetime.combine(duration_date, dt.time())) - 1
                hours[hour_index] += duration


        # now normalize
        max_hour = max(hours)
        normalized_hours = [hour / float(max_hour or 1) for hour in hours]

        self.tick_totals = zip(fractions, normalized_hours)




        # tick label format
        if self.minor_tick >= dt.timedelta(days = 28): # month
            step_format = "%b"

        elif self.minor_tick == WEEK: # week
            step_format = "%b %d"
        elif self.minor_tick == DAY: # day
            if (self.end_time - self.start_time) > dt.timedelta(10):
                step_format = "%b %d"
            else:
                step_format = "%a"
        else:
            step_format = "%H<small><sup>%M</sup></small>"


        for bar in self.bars: # remove any previous bars
            self.sprites.remove(bar)

        self.bars = []
        for i, (key, value, normalized) in enumerate(zip(fractions, hours, normalized_hours)):
            bar = VerticalBar(key, step_format, value, normalized)
            bar.z_order = len(fractions) - i
            bar.interactive = self.interactive and self.minor_tick >= DAY and bar.value > 0

            self.add_child(bar)
            self.bars.append(bar)
