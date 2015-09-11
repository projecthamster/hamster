# -*- coding: utf-8 -*-

# Copyright (C) 2008-2009, 2014 Toms Bauģis <toms.baugis at gmail.com>

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

import bisect
import cairo
import datetime as dt

from collections import defaultdict

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import PangoCairo as pangocairo
from gi.repository import Pango as pango

from hamster.lib import graphics
from hamster.lib import stuff



class ActionRow(graphics.Sprite):
    def __init__(self):
        graphics.Sprite.__init__(self)
        self.visible = False

        self.restart = graphics.Icon("view-refresh-symbolic", size=18,
                                     interactive=True,
                                     mouse_cursor=gdk.CursorType.HAND1,
                                     y=4)
        self.add_child(self.restart)

        self.width = 50 # Simon says



class Label(object):
    """a much cheaper label that would be suitable for cellrenderer"""
    def __init__(self, x=0, y=0, color=None):
        self.x = x
        self.y = y
        self.color = color
        self._label_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
        self.layout = pangocairo.create_layout(self._label_context)
        self.layout.set_font_description(pango.FontDescription(graphics._font_desc))
        self.layout.set_markup("Hamster") # dummy
        self.height = self.layout.get_pixel_size()[1]

    def _set_text(self, text):
        self.layout.set_markup(text)

    def _show(self, g):
        if self.color:
            g.set_color(self.color)
        pangocairo.show_layout(g.context, self.layout)

    def show(self, g, text, x=0, y=0):
        g.save_context()
        g.move_to(x or self.x, y or self.y)
        self._set_text(text)
        self._show(g)
        g.restore_context()



class FactRow(object):
    def __init__(self):
        self.time_label = Label()
        self.activity_label = Label(x=100)

        self.category_label = Label()
        fontdesc = pango.FontDescription(graphics._font_desc)
        fontdesc.set_size(10 * pango.SCALE)
        self.category_label.layout.set_font_description(fontdesc)


        self.description_label = Label()
        fontdesc = pango.FontDescription(graphics._font_desc)
        fontdesc.set_style(pango.Style.ITALIC)
        self.description_label.layout.set_font_description(fontdesc)

        self.tag_label = Label()
        fontdesc = pango.FontDescription(graphics._font_desc)
        fontdesc.set_size(8 * pango.SCALE)
        self.tag_label.layout.set_font_description(fontdesc)

        self.duration_label = Label()
        self.duration_label.layout.set_alignment(pango.Alignment.RIGHT)
        self.duration_label.layout.set_width(90 * pango.SCALE)

        self.width = 0


    def height(self, fact):
        res = self.activity_label.height + 2 * 3
        if fact.description:
            res += self.description_label.height

        if fact.tags:
            res += self.tag_label.height + 5

        return res


    def _show_tags(self, g, tags, color, bg):
        label = self.tag_label
        label.color = bg

        g.save_context()
        g.translate(2.5, 2.5)
        for tag in tags:
            label._set_text(tag)
            w, h = label.layout.get_pixel_size()
            g.rectangle(0, 0, w + 6, h + 5, 2)
            g.fill(color, 0.5)
            g.move_to(3, 2)
            label._show(g)

            g.translate(w + 10, 0)

        g.restore_context()



    def show(self, g, colors, fact, current=False):
        g.save_context()

        color, bg = colors["normal"], colors["normal_bg"]
        if current:
            color, bg = colors["selected"], colors["selected_bg"]
            g.fill_area(0, 0, self.width, self.height(fact), bg)

        g.translate(5, 2)

        time_label = fact.start_time.strftime("%H:%M -")
        if fact.end_time:
            time_label += fact.end_time.strftime(" %H:%M")

        g.set_color(color)
        self.time_label.show(g, time_label)

        self.activity_label.show(g, stuff.escape_pango(fact.activity))
        if fact.category:
            g.save_context()
            g.set_color(color if current else "#999")
            x = self.activity_label.x + self.activity_label.layout.get_pixel_size()[0]
            self.category_label.show(g, "  - %s" % stuff.escape_pango(fact.category), x=x, y=2)
            g.restore_context()

        if fact.description or fact.tags:
            g.save_context()
            g.translate(self.activity_label.x, self.activity_label.height + 3)

            if fact.tags:
                self._show_tags(g, fact.tags, color, bg)
                g.translate(0, self.tag_label.height + 5)

            if fact.description:
                self.description_label.show(g, "<small>%s</small>" % stuff.escape_pango(fact.description))
            g.restore_context()

        self.duration_label.show(g, stuff.format_duration(fact.delta), x=self.width - 105)

        g.restore_context()




class FactTree(graphics.Scene, gtk.Scrollable):
    """
    The fact tree is a painter - it maintains scroll state and shows what we can
    see. That means it does not show all the facts there are, but rather only
    those that you can see.
    It's also painter as it reuses labels. Caching is futile, we do all the painting
    every time



    ASCII Art!
    | Weekday    | Start - End | Activity - category   [actions]| Duration |
    | Month, Day |             | tags, description              |          |
    |            | Start - End | Activity - category            | Duration |

    Inline edit?

    """

    __gsignals__ = {
        # enter or double-click, passes in current day and fact
        'on-activate-row': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        'on-delete-called': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }



    hadjustment = gobject.property(type=gtk.Adjustment, default=None)
    hscroll_policy = gobject.property(type=gtk.ScrollablePolicy, default=gtk.ScrollablePolicy.MINIMUM)
    vadjustment = gobject.property(type=gtk.Adjustment, default=None)
    vscroll_policy = gobject.property(type=gtk.ScrollablePolicy, default=gtk.ScrollablePolicy.MINIMUM)

    def __init__(self):
        graphics.Scene.__init__(self, style_class=gtk.STYLE_CLASS_VIEW)

        self.date_label = Label(10, 3)
        fontdesc = pango.FontDescription(graphics._font_desc)
        fontdesc.set_weight(pango.Weight.BOLD)
        self.date_label.layout.set_alignment(pango.Alignment.RIGHT)
        self.date_label.layout.set_width(80 * pango.SCALE)
        self.date_label.layout.set_font_description(fontdesc)

        self.fact_row = FactRow()

        self.action_row = ActionRow()
        #self.add_child(self.action_row)

        self.row_positions = []
        self.row_heights = []

        self.y = 0
        self.day_padding = 20

        self.hover_day = None
        self.hover_fact = None
        self.current_fact = None

        self.style = self._style

        self.visible_range = None
        self.set_size_request(500, 400)

        self.connect("on-mouse-scroll", self.on_scroll)
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-mouse-down", self.on_mouse_down)

        self.connect("on-resize", self.on_resize)
        self.connect("on-key-press", self.on_key_press)
        self.connect("notify::vadjustment", self._on_vadjustment_change)
        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-double-click", self.on_double_click)


    def on_mouse_down(self, scene, event):
        self.grab_focus()
        if self.hover_fact:
            self.set_current_fact(self.facts.index(self.hover_fact))


    def activate_row(self, day, fact):
        self.emit("on-activate-row", day, fact)

    def delete_row(self, fact):
        if fact:
            self.emit("on-delete-called", fact)

    def on_double_click(self, scene, event):
        if self.hover_fact:
            self.activate_row(self.hover_day, self.hover_fact)

    def on_key_press(self, scene, event):
        if event.keyval == gdk.KEY_Up:
            idx = self.facts.index(self.current_fact) if self.current_fact else 1
            self.set_current_fact(idx - 1)

        elif event.keyval == gdk.KEY_Down:
            idx = self.facts.index(self.current_fact) if self.current_fact else -1
            self.set_current_fact(idx + 1)

        elif event.keyval == gdk.KEY_Page_Down:
            self.y += self.height * 0.8
            self.on_scroll()

        elif event.keyval == gdk.KEY_Page_Up:
            self.y -= self.height * 0.8
            self.on_scroll()

        elif event.keyval == gdk.KEY_Home:
            self.set_current_fact(0)

        elif event.keyval == gdk.KEY_End:
            self.set_current_fact(len(self.facts) - 1)

        elif event.keyval == gdk.KEY_Return:
            self.activate_row(self.hover_day, self.current_fact)

        elif event.keyval == gdk.KEY_Delete:
            self.delete_row(self.current_fact)


    def set_current_fact(self, idx):
        idx = max(0, min(len(self.facts) - 1, idx))
        fact = self.facts[idx]
        self.current_fact = fact

        if fact.y < self.y:
            self.y = fact.y
        if (fact.y + 25) > (self.y + self.height):
            self.y = fact.y - self.height + 25

        self.on_scroll()


    def get_visible_range(self):
        start, end = (bisect.bisect(self.row_positions, self.y) - 1,
                      bisect.bisect(self.row_positions, self.y + self.height))

        y = self.y
        return [{"i": start + i, "y": pos - y, "h": height, "day": day, "facts": facts}
                    for i, (pos, height, (day, facts)) in enumerate(zip(self.row_positions[start:end],
                                                                        self.row_heights[start:end],
                                                                        self.days[start:end]))]


    def on_mouse_move(self, tree, event):
        hover_day, hover_fact = None, None

        for rec in self.visible_range:
            if rec['y'] <= event.y <= (rec['y'] + rec['h']):
                hover_day = rec
                break

        blank_day = hover_day and not hover_day.get('facts')

        if self.hover_day:
            for fact in self.hover_day.get('facts', []):
                if (fact.y - self.y) <= event.y <= (fact.y - self.y + fact.height):
                    hover_fact = fact
                    break

        if hover_day != self.hover_day:
            self.hover_day = hover_day
            self.redraw()

        if hover_fact != self.hover_fact:
            self.hover_fact = hover_fact
            self.move_actions()

    def move_actions(self):
        if self.hover_fact:
            self.action_row.visible = True
            self.action_row.x = self.width - 80 - self.action_row.width
            self.action_row.y = self.hover_fact.y - self.y
        else:
            self.action_row.visible = False


    def _on_vadjustment_change(self, scene, vadjustment):
        if not self.vadjustment:
            return
        self.vadjustment.connect("value_changed", self.on_scroll_value_changed)
        self.set_size_request(500, 300)


    def set_facts(self, facts):
        current_fact, current_date = self.current_fact, self.hover_day

        self.y = 0
        self.hover_fact = None
        if self.vadjustment:
            self.vadjustment.set_value(0)

        if facts:
            start, end = facts[0].date, facts[-1].date
            self.current_fact = facts[0]
        else:
            start = end = dt.datetime.now()
            self.current_fact = None

        by_date = defaultdict(list)
        for fact in facts:
            by_date[fact.date].append(fact)

        days = []
        for i in range((end-start).days + 1):
            current_date = start + dt.timedelta(days=i)
            days.append((current_date, by_date[current_date]))

        self.days = days
        self.facts = facts

        self.set_row_heights()

        if self.height:
            if current_fact:
                fact_ids = [fact.id for fact in facts]
                if current_fact.id in fact_ids:
                    self.set_current_fact(fact_ids.index(current_fact.id))

            elif current_date:
                for i, fact in enumerate(facts):
                    if fact.date == current_date:
                        self.set_current_fact(i)
                        break

            self.on_scroll()


    def set_row_heights(self):
        """
            the row height is defined by following factors:
                * how many facts are there in the day
                * does the fact have description / tags

            This func creates a list of row start positions to be able to
            quickly determine what to display
        """
        if not self.height:
            return

        y, pos, heights = 0, [], []

        for date, facts in self.days:
            height = 0
            for fact in facts:
                fact_height = self.fact_row.height(fact)
                fact.y = y + height
                fact.height = fact_height

                height += fact.height

            height += self.day_padding

            if not facts:
                height = 10
            else:
                height = max(height, 60)

            pos.append(y)
            heights.append(height)
            y += height


        self.row_positions, self.row_heights = pos, heights

        maxy = max(y, 1)

        if self.vadjustment:
            self.vadjustment.set_lower(0)
            self.vadjustment.set_upper(max(maxy, self.height))
            self.vadjustment.set_page_size(self.height)


    def on_resize(self, scene, event):
        self.set_row_heights()
        self.fact_row.width = self.width - 105
        self.on_scroll()


    def on_scroll_value_changed(self, scroll):
        self.y = int(scroll.get_value())
        self.on_scroll()


    def on_scroll(self, scene=None, event=None):
        y_pos = self.y
        direction = 0
        if event and event.direction == gdk.ScrollDirection.UP:
            direction = -1
        elif event and event.direction == gdk.ScrollDirection.DOWN:
            direction = 1

        y_pos += 15 * direction
        if self.vadjustment:
            y_pos = max(0, min(self.vadjustment.get_upper() - self.height, y_pos))
            self.vadjustment.set_value(y_pos)
        self.y = y_pos

        self.move_actions()
        self.redraw()

        self.visible_range = self.get_visible_range()


    def on_enter_frame(self, scene, context):
        has_focus = self.get_toplevel().has_toplevel_focus()
        if has_focus:
            colors = {
                "normal": self.style.get_color(gtk.StateFlags.NORMAL),
                "normal_bg": self.style.get_background_color(gtk.StateFlags.NORMAL),
                "selected": self.style.get_color(gtk.StateFlags.SELECTED),
                "selected_bg": self.style.get_background_color(gtk.StateFlags.SELECTED),
            }
        else:
            colors = {
                "normal": self.style.get_color(gtk.StateFlags.BACKDROP),
                "normal_bg": self.style.get_background_color(gtk.StateFlags.BACKDROP),
                "selected": self.style.get_color(gtk.StateFlags.BACKDROP),
                "selected_bg": self.style.get_background_color(gtk.StateFlags.BACKDROP),
            }


        if not self.height:
            return

        g = graphics.Graphics(context)

        g.set_line_style(1)
        g.translate(0.5, 0.5)

        g.fill_area(0, 0, 105, self.height, "#dfdfdf")


        y = int(self.y)

        for rec in self.visible_range:
            g.save_context()
            g.translate(0, rec['y'])

            if not rec['facts']:
                "do a collapsy thing"
                g.rectangle(0, 0, self.width, 10)
                g.clip()
                g.rectangle(0, 0, self.width, 10)
                g.fill("#eee")

                g.move_to(0, 0)
                g.line_to(self.width, 0)
                g.stroke("#ccc")
                g.restore_context()
                continue


            g.set_color(colors["normal"])
            self.date_label.show(g, rec['day'].strftime("%A\n%b %d"))

            g.translate(105, 0)
            for fact in rec['facts']:
                self.fact_row.show(g, colors, fact, fact==self.current_fact)
                g.translate(0, self.fact_row.height(fact))


            g.restore_context()
