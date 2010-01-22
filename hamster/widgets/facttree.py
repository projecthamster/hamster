# - coding: utf-8 -

# Copyright (C) 2008-2009 Toms Bauģis <toms.baugis at gmail.com>

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
import datetime as dt

from .hamster import stuff
from .hamster.stuff import format_duration, format_activity
from tags import Tag

import pango

def parent_painter(column, cell, model, iter):
    fact = model.get_value(iter, 0)
    parent_info = model.get_value(iter, 1)

    if fact is None:
        parent_info["first"] = model.get_path(iter) == (0,) # first row
        cell.set_property('data', parent_info)
    else:
        cell.set_property('data', fact)

def action_painter(column, cell, model, iter):
    cell.set_property('xalign', 1)
    cell.set_property('yalign', 0)

    if model.get_value(iter, 0) is None:
        cell.set_property("stock_id", "")
    else:
        cell.set_property("stock_id", "gtk-edit")


class FactTree(gtk.TreeView):
    __gsignals__ = {
        "edit-clicked": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "double-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, ))
    }

    def __init__(self):
        gtk.TreeView.__init__(self)

        self.set_headers_visible(False)
        self.set_show_expanders(False)

        # fact (None for parent), duration, parent data (if any)
        self.store_model = gtk.ListStore(gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)
        self.set_model(self.store_model)


        fact_cell = FactCellRenderer()
        fact_column = gtk.TreeViewColumn("", fact_cell, data=0)
        fact_column.set_cell_data_func(fact_cell, parent_painter)
        fact_column.set_expand(True)
        self.append_column(fact_column)

        edit_cell = gtk.CellRendererPixbuf()
        edit_cell.set_property("ypad", 2)
        edit_cell.set_property("mode", gtk.CELL_RENDERER_MODE_ACTIVATABLE)
        self.edit_column = gtk.TreeViewColumn("", edit_cell)
        self.edit_column.set_cell_data_func(edit_cell, action_painter)
        self.append_column(self.edit_column)

        self.connect("row-activated", self._on_row_activated)
        self.connect("button-release-event", self._on_button_release_event)
        self.connect("key-press-event", self._on_key_pressed)
        self.connect("configure-event", lambda *args: self.columns_autosize())

        self.show()

        self.longest_activity_category = 0 # we will need this for the cell renderer
        self.longest_interval = 0 # we will need this for the cell renderer
        self.longest_duration = 0 # we will need this for the cell renderer
        self.stored_selection = []

        self.box = None


        pixmap = gtk.gdk.Pixmap(None, 10, 10, 24)
        _test_context = pixmap.cairo_create()
        self._test_layout = _test_context.create_layout()
        font = pango.FontDescription(gtk.Style().font_desc.to_string())
        self._test_layout.set_font_description(font)


    def fix_row_heights(self):
        alloc = self.get_allocation()
        if alloc != self.box:
            self.box = alloc
            self.columns_autosize()

    def clear(self):
        self.store_model.clear()
        self.longest_activity_category = 0
        self.longest_interval = 0
        self.longest_duration = 0

    def update_longest_dimensions(self, fact):
        interval = "%s -" % fact["start_time"].strftime("%H:%M")
        if fact["end_time"]:
            interval = "%s %s" % (interval, fact["end_time"].strftime("%H:%M"))
        self._test_layout.set_markup(interval)
        w, h = self._test_layout.get_pixel_size()
        self.longest_interval = max(self.longest_interval, w + 20)


        self._test_layout.set_markup("%s - <small>%s</small> " % (fact["name"], fact["category"]))
        w, h = self._test_layout.get_pixel_size()
        self.longest_activity_category = max(self.longest_activity_category, w + 10)

        self._test_layout.set_markup("%s" % stuff.format_duration(fact["delta"]))
        w, h = self._test_layout.get_pixel_size()
        self.longest_duration = max(self.longest_duration, w)


    def add_fact(self, fact):
        self.update_longest_dimensions(fact)
        self.store_model.append([fact, None])


    def add_group(self, group_label, group_date, facts):
        total = sum([stuff.duration_minutes(fact["delta"]) for fact in facts])

        # adds group of facts with the given label
        self.store_model.append([None, dict(date = group_date,
                                            label = group_label,
                                            duration = total)])

        for fact in facts:
            self.add_fact(fact)

        self.expand_all()


    def get_row(self, path):
        """checks if the path is valid and if so, returns the model row"""
        if path is None or path < 0: return None

        try: # see if path is still valid
            iter = self.store_model.get_iter(path)
            return self.store_model[path]
        except:
            return None

    def id_or_label(self, path):
        """returns id or date, id if it is a fact row or date if it is a group row"""
        row = self.get_row(path)
        if not row: return None

        if row[0]:
            return row[0]['id']
        else:
            return row[1]['label']

    def detach_model(self):
        # ooh, somebody is going for refresh!
        # let's save selection too - maybe it will come handy
        self.store_selection()

        # and now do what we were asked to
        self.set_model()


    def attach_model(self):
        # attach model is also where we calculate the bounding box widths
        self.set_model(self.store_model)
        self.expand_all()

        if self.stored_selection:
            self.restore_selection()


    def store_selection(self):
        selection = self.get_selection()
        model, iter = selection.get_selected()

        if iter:
            path = model.get_path(iter)[0]
            prev, cur, next = path - 1, path, path + 1
            self.stored_selection = ((prev, self.id_or_label(prev)),
                                     (cur, self.id_or_label(cur)),
                                     (next, self.id_or_label(next)))


    def restore_selection(self):
        """the code is quite hairy, but works with all kinds of deletes
           and does not select row when it should not.
           TODO - it might be worth replacing this with something much simpler"""
        model = self.store_model

        new_prev_val, new_cur_val, new_next_val = None, None, None
        prev, cur, next = self.stored_selection

        if cur:  new_cur_val  = self.id_or_label(cur[0])
        if prev: new_prev_val = self.id_or_label(prev[0])
        if next: new_next_val = self.id_or_label(next[0])

        path = None
        values = (new_prev_val, new_cur_val, new_next_val)
        paths = (prev, cur, next)

        if cur[1] and cur[1] in values: # simple case
            # look if we can find previous current in the new threesome
            path = paths[values.index(cur[1])][0]
        elif prev[1] and prev[1] == new_prev_val and next[1] and next[1] == new_next_val:
            # on update the ID changes so we find it by matching in between
            path = cur[0]
        elif prev[1] and prev[1] == new_prev_val: # all that's left is delete.
            if new_cur_val:
                path = cur[0]
            else:
                path = prev[0]
        elif not new_prev_val and not new_next_val and new_cur_val:
            # the only record in the tree (no next no previous, but there is current)
            path = cur[0]


        if path is not None:
            selection = self.get_selection()
            selection.select_path(path)

            self.scroll_to_cell(path)

    def select_fact(self, fact_id):
        i = 0
        while self.id_or_label(i) and self.id_or_label(i) != fact_id:
            i +=1

        if self.id_or_label(i) == fact_id:
            selection = self.get_selection()
            selection.select_path(i)

    def get_selected_fact(self):
        selection = self.get_selection()
        (model, iter) = selection.get_selected()
        if iter:
            return model[iter][0] or model[iter][1]["date"]
        else:
            return None


    def _on_button_release_event(self, tree, event):
        # a hackish solution to make edit icon keyboard accessible
        pointer = event.window.get_pointer() # x, y, flags
        path = self.get_path_at_pos(pointer[0], pointer[1]) #column, innerx, innery

        if path and path[1] == self.edit_column:
            self.emit("edit-clicked", self.get_selected_fact())
            return True

        return False

    def _on_row_activated(self, tree, path, column):
        if column == self.edit_column:
            self.emit_stop_by_name ('row-activated')
            self.emit("edit-clicked", self.get_selected_fact())
            return True


    def _on_key_pressed(self, tree, event):
        # capture ctrl+e and pretend that user click on edit
        if (event.keyval == gtk.keysyms.e  \
              and event.state & gtk.gdk.CONTROL_MASK):
            self.emit("edit-clicked", self.get_selected_fact())
            return True

        return False



class FactCellRenderer(gtk.GenericCellRenderer):
    """ We need all kinds of wrapping and spanning and the treeview just does
        not cut it"""

    __gproperties__ = {
        "data": (gobject.TYPE_PYOBJECT, "Data", "Data", gobject.PARAM_READWRITE),
    }

    def __init__(self):
        gtk.GenericCellRenderer.__init__(self)
        self.height = 0
        self.data = None

        default_font = gtk.Style().font_desc.to_string()
        self.label_font = pango.FontDescription(default_font)
        self.label_font_size = 10

        self.selected_color = gtk.Style().text[gtk.STATE_SELECTED]
        self.normal_color = gtk.Style().text[gtk.STATE_NORMAL]

        self.tag_font = pango.FontDescription(default_font)
        self.tag_font.set_size(pango.SCALE * 8)

        self.layout, self.tag_layout = None, None

        self.col_padding = 10
        self.row_padding = 4


        self.labels = {}

    def do_set_property (self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr (self, pspec.name)


    def set_text(self, text):
        # sets text and returns width and height of the layout
        self.layout.set_text(text)
        w, h = self.layout.get_pixel_size()
        return w, h

    def on_render (self, window, widget, background_area, cell_area, expose_area, flags):
        if not self.data:
            return

        """
          ASCII Art
          --------------+--------------------------------------------+-------+---+
          13:12 - 17:18 | Some activity - category, tag, tag, tag,   | 14:44 | E |
                        | tag, tag, some description in grey italics |       |   |
          --------------+--------------------------------------------+-------+---+
        """


        context = window.cairo_create()
        if not self.layout:
            self.layout = context.create_layout()
            self.layout.set_font_description(self.label_font)

            self.tag_layout = context.create_layout()
            self.tag_layout.set_font_description(self.tag_font)


        if "id" in self.data:
            fact, parent = self.data, None
        else:
            parent, fact = self.data, None




        x, y, width, height = cell_area
        context.translate(x, y)

        current_fact = widget.get_selected_fact()

        if parent:
            text_color = self.normal_color
            # if we are selected, change font color appropriately
            if current_fact and isinstance(current_fact, dt.date) \
               and current_fact == parent["date"]:
                text_color = self.selected_color

            self.set_color(context, text_color)

            self.layout.set_markup("<b>%s</b>" % stuff.escape_pango(parent["label"]))
            if self.data["first"]:
                y = 5
            else:
                y = 20

            context.move_to(5, y)
            context.show_layout(self.layout)

            self.layout.set_markup("<b>%s</b>" % stuff.format_duration(parent["duration"]))
            label_w, label_h = self.layout.get_pixel_size()

            context.move_to(width - label_w, y)
            context.show_layout(self.layout)

        else:
            text_color = self.normal_color
            selected = False
            # if we are selected, change font color appropriately
            if current_fact and isinstance(current_fact, dt.date) == False \
               and current_fact["id"] == fact["id"]:
                text_color = self.selected_color
                selected = True

            def show_label(label, x, y, w):
                self.layout.set_markup(label)
                context.move_to(x, y)
                if w:
                    self.layout.set_width(w)
                context.show_layout(self.layout)

            self.set_color(context, text_color)

            labels = self.labels[fact["id"]]
            show_label(*labels["interval"])

            # for the right-aligned delta with have reserved space for scrollbar
            # but about it's existance we find only on expose, so we realign
            self.layout.set_markup(labels["delta"][0])
            w, h = self.layout.get_pixel_size()
            context.move_to(width - w, labels["delta"][2])
            context.show_layout(self.layout)

            show_label(*labels["activity"])

            if fact["category"]:
                if not selected:
                    self.set_color(context, widget.get_style().text[gtk.STATE_INSENSITIVE])

                show_label(*labels["category"])


            if fact["tags"]:
                start_x, start_y, cell_end = labels["tags"][1:]
                cur_x, cur_y = start_x, start_y

                for i, tag in enumerate(fact["tags"]):
                    tag_w, tag_h = Tag.tag_size(tag, self.tag_layout)

                    if i > 0 and cur_x + tag_w >= cell_end:
                        cur_x = start_x
                        cur_y += tag_h + 4

                    Tag(context, self.tag_layout, True, tag, None,
                        gtk.gdk.Rectangle(cur_x, cur_y, cell_end - cur_x, height - cur_y))

                    cur_x += tag_w + 4


            if fact["description"]:
                self.set_color(context, text_color)
                show_label(*labels["description"])



    def set_color(self, context, color):
        context.set_source_rgba(*self.color_to_cairo_rgba(color))

    def color_to_cairo_rgba(self, c, a=1):
        return c.red/65535.0, c.green/65535.0, c.blue/65535.0, a


    def get_fact_size(self, widget):
        """determine size and save calculated coordinates"""

        if not self.data or "id" not in self.data:
            return None
        fact = self.data
        pixmap = gtk.gdk.Pixmap(None, 10, 10, 24)
        context = pixmap.cairo_create()

        layout = context.create_layout()
        layout.set_font_description(self.label_font)
        x, y, width, height = widget.get_allocation()

        labels = {}

        cell_width = width - 45

        """ start time and end time at beginning of column """
        interval = fact["start_time"].strftime("%H:%M -")
        if fact["end_time"]:
            interval = "%s %s" % (interval, fact["end_time"].strftime("%H:%M"))
        labels["interval"] = (interval, self.col_padding, 2, -1)

        """ duration at the end """
        delta = stuff.format_duration(fact["delta"])
        layout.set_markup(delta)
        duration_w, duration_h = layout.get_pixel_size()
        labels["delta"] = (delta, cell_width - duration_w, 2, -1)


        """ activity, category, tags, description in middle """
        # we want our columns look aligned, so we will do fixed offset from
        # both sides, in letter length

        cell_start = widget.longest_interval
        cell_width = cell_width - widget.longest_interval - widget.longest_duration


        layout.set_markup(stuff.escape_pango(fact["name"]))
        label_w, label_h = layout.get_pixel_size()

        labels["activity"] = (stuff.escape_pango(fact["name"]), cell_start, 2, -1)
        labels["category"] = (" - <small>%s</small>" % stuff.escape_pango(fact["category"]),
                              cell_start + label_w, 2, -1)


        tag_cell_start = cell_start + widget.longest_activity_category
        tag_cell_end = cell_start + cell_width

        cell_height = label_h + 4

        cur_x, cur_y = tag_cell_start, 2
        if fact["tags"]:
            layout.set_font_description(self.tag_font)

            for i, tag in enumerate(fact["tags"]):
                tag_w, tag_h = Tag.tag_size(tag, layout)

                if i > 0 and cur_x + tag_w >= tag_cell_end:
                    cur_x = tag_cell_start
                    cur_y += tag_h + 4
                cur_x += tag_w + 4

            cell_height = max(cell_height, cur_y + tag_h + 4)

            labels["tags"] = (None, tag_cell_start, 2, tag_cell_end)

            layout.set_font_description(self.label_font)


        # see if we can fit in single line
        # if not, put description under activity
        if fact["description"]:
            description = "<small>%s</small>" % stuff.escape_pango(fact["description"])
            layout.set_markup(description)
            label_w, label_h = layout.get_pixel_size()

            x, y = cur_x, cur_y
            width = cell_start + cell_width - x

            if x + label_w > width:
                x = cell_start
                y = cell_height
                width = cell_width

            layout.set_width(width * pango.SCALE)
            label_w, label_h = layout.get_pixel_size()

            labels["description"] = (description, x, y, width * pango.SCALE)

            cell_height += label_h + 4

        self.labels[fact["id"]] = labels
        return (0, 0, 0, cell_height)


    def on_get_size (self, widget, cell_area):
        if "id" in self.data: # fact
            return self.get_fact_size(widget)
        else:
            if self.data["first"]:
                return (0, 0, 0, 25)
            else:
                return (0, 0, 0, 40)
