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

from collections import defaultdict
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import PangoCairo as pangocairo
from gi.repository import Pango as pango

from hamster.lib import datetime as dt
from hamster.lib import graphics
from hamster.lib import stuff
from hamster.lib.fact import Fact


class TotalFact(Fact):
    """An extension of Fact that is used for daily totals.
    Instances of this class are rendered differently than instances
    of Fact.
    A TotalFact doesn't have a meaningful  start and an end, but a
    total duration (delta).
    FIXME: Ideally, we should have a common parent for Fact and Total Fact
    so we don't need to have nonsensical start and end properties here.
    """

    def __init__(self, activity, duration):
        super().__init__(activity=activity, start=dt.datetime.now(), end=dt.datetime.now())
        self.duration = duration

    @property
    def delta(self):
        return self.duration


class Label(object):
    """a much cheaper label that would be suitable for cellrenderer"""

    def __init__(self, x=0, y=0, color=None):
        self.x = x
        self.y = y
        self.color = color
        self._label_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
        self.layout = pangocairo.create_layout(self._label_context)
        self.layout.set_font_description(pango.FontDescription(graphics._font_desc))
        self.set_text("Hamster")  # dummy

    @property
    def height(self):
        """Label height in pixels."""
        return self.layout.get_pixel_size()[1]

    def set_text(self, text):
        self.text = text
        self.layout.set_markup(text)

    def get_text(self):
        return self.text

    def show(self, g, text=None, x=None, y=None):
        """Show the label.

        If text is given, it overrides any previous set_text().
        x and y can be passed to temporary override the position.
        (self.x and self.y will not be changed)
        """

        g.save_context()

        # fallback to self.x
        if x is None:
            x = self.x
        if y is None:
            y = self.y

        g.move_to(x, y)

        if text is not None:
            self.set_text(text)

        if self.color:
            g.set_color(self.color)
        pangocairo.show_layout(g.context, self.layout)

        g.restore_context()


class TagLabel(Label):
    """Tag label, with small text."""

    def set_text(self, text):
        Label.set_text(self, "<small>{}</small>".format(text))


class FactRow(object):
    def __init__(self):
        self.time_label = Label()
        self.activity_label = Label(x=100)

        self.category_label = Label()
        self.description_label = Label()
        self.tag_label = TagLabel()

        self.duration_label = Label()
        self.duration_label.layout.set_alignment(pango.Alignment.RIGHT)
        self.duration_label.layout.set_width(90 * pango.SCALE)

        self.width = 0

        # margins (in pixels)
        self.tag_row_margin_H = 2.5
        self.tag_row_margin_V = 2.5
        self.tag_inner_margin_H = 3
        self.tag_inner_margin_V = 2
        self.inter_tag_margin = 4
        self.row_margin_H = 5
        self.row_margin_V = 2
        self.category_offset_V = self.category_label.height * 0.1

    @property
    def height(self):
        res = self.activity_label.height + 2 * 3
        if self.fact.description:
            res += self.description_label.height

        if self.fact.tags:
            res += (self.tag_label.height
                    + self.tag_inner_margin_V * 2
                    + self.tag_row_margin_V * 2)

        res += self.row_margin_V * 2

        return res

    def set_fact(self, fact):
        """Set current fact."""

        self.fact = fact

        time_label = fact.start_time.strftime("%H:%M -")
        if fact.end_time:
            time_label += fact.end_time.strftime(" %H:%M")
        self.time_label.set_text(time_label)

        self.activity_label.set_text(stuff.escape_pango(fact.activity))

        category_text = "  - {}".format(stuff.escape_pango(fact.category)) if fact.category else ""
        self.category_label.set_text(category_text)

        text = stuff.escape_pango(fact.description)
        description_text = "<small><i>{}</i></small>".format(text) if fact.description else ""
        self.description_label.set_text(description_text)

        if fact.tags:
            # for now, tags are on a single line.
            # The first one is enough to determine the height.
            self.tag_label.set_text(stuff.escape_pango(fact.tags[0]))

    def _show_tags(self, g, color, bg):
        label = self.tag_label
        label.color = bg

        g.save_context()
        g.translate(self.tag_row_margin_H, self.tag_row_margin_V)
        for tag in self.fact.tags:
            label.set_text(stuff.escape_pango(tag))
            w, h = label.layout.get_pixel_size()
            rw = w + self.tag_inner_margin_H * 2
            rh = h + self.tag_inner_margin_V * 2
            g.rectangle(0, 0, rw, rh, 2)
            g.fill(color, 0.5)
            label.show(g, x=self.tag_inner_margin_H, y=self.tag_inner_margin_V)

            g.translate(rw + self.inter_tag_margin, 0)

        g.restore_context()

    def show(self, g, colors, fact=None, is_selected=False):
        """Display the fact row.

        If fact is given, the fact attribute is updated.
        """
        g.save_context()

        if fact is not None:
            # before the selection highlight, to get the correct height
            self.set_fact(fact)

        color, bg = colors["normal"], colors["normal_bg"]
        if is_selected:
            color, bg = colors["selected"], colors["selected_bg"]
            g.fill_area(0, 0, self.width, self.height, bg)

        g.translate(self.row_margin_H, self.row_margin_V)

        g.set_color(color)

        # Do not show the start/end time for Totals
        if not isinstance(self.fact, TotalFact):
            self.time_label.show(g)
        self.activity_label.show(g, self.activity_label.get_text() if not isinstance(self.fact, TotalFact) else "<b>{}</b>".format(self.activity_label.get_text()))

        if self.fact.category:
            g.save_context()
            category_color = graphics.ColorUtils.mix(bg, color, 0.57)
            g.set_color(category_color)
            x = self.activity_label.x + self.activity_label.layout.get_pixel_size()[0]
            self.category_label.show(g, x=x, y=self.category_offset_V)
            g.restore_context()

        if self.fact.description or self.fact.tags:
            g.save_context()
            g.translate(self.activity_label.x, self.activity_label.height + 3)

            if self.fact.tags:
                self._show_tags(g, color, bg)
                tag_height = (self.tag_label.height
                              + self.tag_inner_margin_V * 2
                              + self.tag_row_margin_V * 2)
                g.translate(0, tag_height)

            if self.fact.description:
                self.description_label.show(g)

            g.restore_context()

        self.duration_label.show(g, self.fact.delta.format() if not isinstance(self.fact, TotalFact) else "<b>{}</b>".format(self.fact.delta.format()), x=self.width - 105)

        g.restore_context()


class FactTree(gtk.DrawingArea):
    """
    The fact tree is a painter.
    It does not change facts by itself, only sends signals.
    Facts get updated only through `set_facts`.

    It maintains scroll state and shows what we can see.
    That means it does not show all the facts there are,
    but rather only those that you can see.
    It's also painter as it reuses labels.
    Caching is futile, we do all the painting every time


    ASCII Art!
    | Weekday    | Start - End | Activity - category   [actions]| Duration       |
    | Month, Day |             | tags, description              |                |
    |            | Start - End | Activity - category            | Duration       |
    |            |             | Total                          | Total Duration |

    Inline edit?

    """

    __gsignals__ = {
        # enter or double-click, passes in current day and fact
        'on-activate-row': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        'on-delete-called': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    hadjustment = gobject.property(type=gtk.Adjustment, default=None)
    hscroll_policy = gobject.property(type=gtk.ScrollablePolicy, default=gtk.ScrollablePolicy.MINIMUM)
    vadjustment = gobject.property(type=gtk.Adjustment, default=None)
    vscroll_policy = gobject.property(type=gtk.ScrollablePolicy, default=gtk.ScrollablePolicy.MINIMUM)

    def __init__(self):
        super().__init__()

        self.date_label = Label(10, 3)
        fontdesc = pango.FontDescription(graphics._font_desc)
        fontdesc.set_weight(pango.Weight.BOLD)
        self.date_label.layout.set_alignment(pango.Alignment.RIGHT)
        self.date_label.layout.set_width(80 * pango.SCALE)
        self.date_label.layout.set_font_description(fontdesc)

        self.fact_row = FactRow()

        self.row_positions = []
        self.row_heights = []

        self.day_padding = 20

        self.current_fact = None

        self.colors = graphics.Colors
        self.style = self.get_style_context()
        self.style.add_class(gtk.STYLE_CLASS_VIEW)

        self.visible_range = None
        self.set_size_request(500, 400)

        self.set_can_focus(True)
        self.set_events(gdk.EventMask.BUTTON_PRESS_MASK
                        | gdk.EventMask.KEY_PRESS_MASK)
        self.connect("button-press-event", self.on_mouse_down)
        self.connect("key-press-event", self.on_key_press)

    @property
    def current_fact_index(self):
        """Current fact index in the self.facts list."""
        facts_ids = [fact.id for fact in self.facts]
        return facts_ids.index(self.current_fact.id)

    def on_mouse_down(self, widget, event):
        hover_fact = self.get_hover_fact(event.y)

        if event.type == gdk.EventType.BUTTON_PRESS:
            self.grab_focus()
            if hover_fact:
                # match either content or id
                if (hover_fact == self.current_fact
                        or (hover_fact
                            and self.current_fact
                            and hover_fact.id == self.current_fact.id)
                        ):
                    self.unset_current_fact()
                # Totals can't be selected
                elif not isinstance(hover_fact, TotalFact):
                    self.set_current_fact(hover_fact)
                self.queue_draw()
        elif event.type == gdk.EventType._2BUTTON_PRESS:
            if hover_fact and not isinstance(hover_fact, TotalFact):
                self.activate_row(hover_fact)

    def activate_row(self, fact):
        self.emit("on-activate-row", fact)

    def delete_row(self, fact):
        self.emit("on-delete-called", fact)

    def on_key_press(self, widget, event):
        # all keys should appear also in the Overview.on_key_press
        # to be forwarded here even without focus.
        if event.keyval == gdk.KEY_Up:
            if self.facts:
                if self.current_fact:
                    idx = max(0, self.current_fact_index - 1)
                else:
                    # enter from below
                    idx = len(self.facts) - 1
                self.set_current_fact(self.facts[idx])

        elif event.keyval == gdk.KEY_Down:
            if self.facts:
                if self.current_fact:
                    idx = min(len(self.facts) - 1, self.current_fact_index + 1)
                else:
                    # enter from top
                    idx = 0
                self.set_current_fact(self.facts[idx])

        elif event.keyval == gdk.KEY_Home:
            if self.facts:
                self.set_current_fact(self.facts[0])

        elif event.keyval == gdk.KEY_End:
            if self.facts:
                self.set_current_fact(self.facts[-1])

        elif event.keyval == gdk.KEY_Return:
            if self.current_fact:
                self.activate_row(self.current_fact)

        elif event.keyval == gdk.KEY_Delete:
            if self.current_fact:
                self.delete_row(self.current_fact)

    def set_current_fact(self, fact):
        self.current_fact = fact

        self.scroll_to(fact=fact)
        self.queue_draw()

    def scroll_to(self, y=0, fact=None):
        # If we are inside a scrollable viewport, that viewport will
        # have a vadjustment property that stores the scroll position,
        # so update that here.
        parent = self.get_parent()
        if parent and hasattr(parent, 'get_vadjustment'):
            vadj = parent.get_vadjustment()
            if fact is not None:
                vadj.clamp_page(fact.y, fact.y + fact.height)
            else:
                vadj.set_value(y)

        self.queue_draw()

    def unset_current_fact(self):
        """Deselect fact."""
        self.current_fact = None
        self.queue_draw()

    def get_visible_range(self, y0, y1):
        start, end = (max(0, bisect.bisect(self.row_positions, y0) - 1),
                      bisect.bisect(self.row_positions, y1))

        return [{"i": start + i, "y": pos, "h": height, "day": day, "facts": facts}
                for i, (pos, height, (day, facts)) in enumerate(zip(self.row_positions[start:end],
                                                                    self.row_heights[start:end],
                                                                    self.days[start:end]))]

    def get_hover_fact(self, y):
        facts = []

        candidate = bisect.bisect(self.row_positions, y) - 1
        if candidate >= 0 and y < self.row_positions[candidate] + self.row_heights[candidate]:
            day, facts = self.days[candidate]

        for fact in facts:
            if fact.y <= y <= (fact.y + fact.height):
                return fact

        return None


    def set_facts(self, facts, scroll_to_top=False):
        # FactTree adds attributes to its facts. isolate these side effects
        # copy the id too; most of the checks are based on id here.
        self.facts = [fact.copy(id=fact.id) for fact in facts]
        del facts  # make sure facts is not used by inadvertance below.

        # If we get an entirely new set of facts, scroll back to the top
        if scroll_to_top:
            self.scroll_to(y=0)
        self.hover_fact = None

        if self.facts:
            start = self.facts[0].date
            end = self.facts[-1].date
        else:
            start = end = dt.hday.today()

        by_date = defaultdict(list)
        delta_by_date = defaultdict(dt.timedelta)
        for fact in self.facts:
            by_date[fact.date].append(fact)
            delta_by_date[fact.date] += fact.delta

        # Add a TotalFact at the end of each day if we are
        # displaying more than one day.
        if len(by_date) > 1:
            for key in by_date:
                total_by_date = TotalFact(_("Total"), delta_by_date[key])
                by_date[key].append(total_by_date)

        days = []
        for i in range((end - start).days + 1):
            current_date = start + dt.timedelta(days=i)
            if current_date in by_date:
                days.append((current_date, by_date[current_date]))

        self.days = days

        self.set_row_heights()

        if (self.current_fact
                and self.current_fact.id in (fact.id for fact in self.facts)
                ):
            self.scroll_to(fact=self.current_fact)
        else:
            self.unset_current_fact()
        self.queue_draw()

    def set_row_heights(self):
        """
            the row height is defined by following factors:
                * how many facts are there in the day
                * does the fact have description / tags

            This func creates a list of row start positions to be able to
            quickly determine what to display
        """
        y, pos, heights = 0, [], []

        for date, facts in self.days:
            height = 0
            for fact in facts:
                self.fact_row.set_fact(fact)
                fact_height = self.fact_row.height
                fact.y = y + height
                fact.height = fact_height

                height += fact.height

            height += self.day_padding
            height = max(height, 60)

            pos.append(y)
            heights.append(height)
            y += height

        self.row_positions, self.row_heights = pos, heights
        self.set_size_request(-1, max(y, 1))

    def do_draw(self, context):
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

        width = self.get_allocation().width
        self.fact_row.width = width - 105

        g = graphics.Graphics(context)

        g.set_line_style(1)
        g.translate(0.5, 0.5)

        # The clip region tells us what part needs to be redrawn. This
        # also prevents drawing things that are outside of the scroll
        # area.
        x0, y0, x1, y1 = context.clip_extents()

        date_bg_color = self.colors.mix(colors["normal_bg"], colors["normal"], 0.15)
        g.fill_area(0, y0, 105, (y1 - y0), date_bg_color)
        g.fill_area(105, y0, width, (y1 - y0), colors["normal_bg"])

        for rec in self.get_visible_range(y0, y1):
            g.save_context()
            g.translate(0, rec['y'])
            g.set_color(colors["normal"])
            self.date_label.show(g, rec['day'].strftime("%A\n%b %d"))

            g.translate(105, 0)
            for fact in rec['facts']:
                is_selected = (self.current_fact is not None
                               and fact.id == self.current_fact.id)
                self.fact_row.set_fact(fact)
                self.fact_row.show(g, colors, is_selected=is_selected)
                g.translate(0, self.fact_row.height)

            g.restore_context()
