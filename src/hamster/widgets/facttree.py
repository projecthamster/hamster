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

"""beware, this code has some major dragons in it. i'll clean it up one day!"""

import gtk, gobject
import cairo
import datetime as dt

from ..lib import stuff, graphics
from tags import Tag

import pango

def parent_painter(column, cell, model, iter):
    row = model.get_value(iter, 0)

    if isinstance(row, FactRow):
        cell.set_property('data', row)
    else:
        row.first = model.get_path(iter) == (0,) # first row
        cell.set_property('data', row)

def action_painter(column, cell, model, iter):
    cell.set_property('xalign', 1)
    cell.set_property('yalign', 0)

    if isinstance(model.get_value(iter, 0), GroupRow):
        cell.set_property("stock_id", "")
    else:
        cell.set_property("stock_id", "gtk-edit")



class GroupRow(object):
    def __init__(self, label, date, duration):
        self.label = label
        self.duration = duration
        self.date = date
        self.first = False # will be set by the painter, used

    def __eq__(self, other):
        return isinstance(other, GroupRow) \
           and self.label == other.label \
           and self.duration == other.duration \
           and self.date == other.date

    def __hash__(self):
        return 1

class FactRow(object):
    def __init__(self, fact):
        self.fact = fact
        self.id = fact.id
        self.name = fact.activity
        self.category = fact.category
        self.description = fact.description
        self.tags = fact.tags
        self.start_time = fact.start_time
        self.end_time = fact.end_time
        self.delta = fact.delta

    def __eq__(self, other):
        return isinstance(other, FactRow) and other.id == self.id \
           and other.name == self.name \
           and other.category == self.category \
           and other.description == self.description \
           and other.tags == self.tags \
           and other.start_time == self.start_time \
           and other.end_time == self.end_time \
           and other.delta == self.delta


    def __hash__(self):
        return self.id

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
        self.store_model = gtk.ListStore(gobject.TYPE_PYOBJECT)
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
        self.connect("key-release-event", self._on_key_released)
        self.connect("configure-event", lambda *args: self.fix_row_heights())
        self.connect("motion-notify-event", self._on_motion)

        self.show()

        self.longest_activity_category = 0 # we will need this for the cell renderer
        self.longest_interval = 0 # we will need this for the cell renderer
        self.longest_duration = 0 # we will need this for the cell renderer
        self.stored_selection = []

        self.box = None


        pixmap = gtk.gdk.Pixmap(None, 10, 10, 1)
        _test_context = pixmap.cairo_create()
        self._test_layout = _test_context.create_layout()
        font = pango.FontDescription(gtk.Style().font_desc.to_string())
        self._test_layout.set_font_description(font)
        self.prev_rows = []
        self.new_rows = []

        self.connect("destroy", self.on_destroy)

    def on_destroy(self, widget):
        for col in self.get_columns():
            col.destroy()
            self.remove_column(col)


    def fix_row_heights(self):
        alloc = self.get_allocation()
        if alloc != self.box:
            self.box = alloc
            self.columns_autosize()

    def clear(self):
        #self.store_model.clear()
        self.longest_activity_category = 0
        self.longest_interval = 0
        self.longest_duration = 0

    def update_longest_dimensions(self, fact):
        interval = "%s -" % fact.start_time.strftime("%H:%M")
        if fact.end_time:
            interval = "%s %s" % (interval, fact.end_time.strftime("%H:%M"))
        self._test_layout.set_markup(interval)
        w, h = self._test_layout.get_pixel_size()
        self.longest_interval = max(self.longest_interval, w + 20)


        self._test_layout.set_markup("%s - <small>%s</small> " % (stuff.escape_pango(fact.name),
                                                                  stuff.escape_pango(fact.category)))
        w, h = self._test_layout.get_pixel_size()
        self.longest_activity_category = max(self.longest_activity_category, w + 10)

        self._test_layout.set_markup("%s" % stuff.format_duration(fact.delta))
        w, h = self._test_layout.get_pixel_size()
        self.longest_duration = max(self.longest_duration, w)


    def add_fact(self, fact):
        fact = FactRow(fact)
        self.update_longest_dimensions(fact)
        self.new_rows.append(fact)


    def add_group(self, group_label, group_date, facts):
        total_duration = stuff.duration_minutes([fact.delta for fact in facts])

        self.new_rows.append(GroupRow(group_label, group_date, total_duration))

        for fact in facts:
            self.add_fact(fact)


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

        if isinstance(row[0], FactRow):
            return row[0].id
        else:
            return row[0].label


    def detach_model(self):
        self.prev_rows = list(self.new_rows)
        self.new_rows = []
        # ooh, somebody is going for refresh!
        # let's save selection too - maybe it will come handy
        self.store_selection()

        #self.parent.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)


        # and now do what we were asked to
        #self.set_model()
        self.clear()


    def attach_model(self):
        prev_rows = set(self.prev_rows)
        new_rows = set(self.new_rows)
        common = set(prev_rows) & set(new_rows)

        if common: # do full refresh only if we don't recognize any rows
            gone = prev_rows - new_rows
            if gone:
                all_rows = len(self.store_model)
                rows = list(self.store_model)
                rows.reverse()

                for i, row in enumerate(rows):
                    if row[0] in gone:
                        self.store_model.remove(self.store_model.get_iter(all_rows - i-1))

                self.prev_rows = [row[0] for row in self.store_model]

            new = new_rows - prev_rows
            if new:
                for i, row in enumerate(self.new_rows):
                    if i <= len(self.store_model) - 1:
                        if row == self.store_model[i][0]:
                            continue

                        self.store_model.insert_before(self.store_model.get_iter(i), (row,))
                    else:
                        self.store_model.append((row, ))


        else:
            self.store_model.clear()
            for row in self.new_rows:
                self.store_model.append((row, ))

        if self.stored_selection:
            self.restore_selection()


    def store_selection(self):
        self.stored_selection = None
        selection = self.get_selection()
        if not selection:
            return

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

            self.set_cursor_on_cell(path)

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
            data = model[iter][0]
            if isinstance(data, FactRow):
                return data.fact
            else:
                return data.date
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


    def _on_key_released(self, tree, event):
        # capture e keypress and pretend that user click on edit
        if (event.keyval == gtk.keysyms.e):
            self.emit("edit-clicked", self.get_selected_fact())
            return True

        return False


    def _on_motion(self, view, event):
        'As the pointer moves across the view, show a tooltip.'

        path = view.get_path_at_pos(int(event.x), int(event.y))

        if path:
            path, col, x, y = path

            model = self.get_model()
            data = model[path][0]

            self.set_tooltip_text(None)

            if isinstance(data, FactRow):
                renderer = view.get_column(0).get_cell_renderers()[0]

                label = data.description
                self.set_tooltip_text(label)

            self.trigger_tooltip_query()



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

        font = gtk.Style().font_desc
        self.default_size = font.get_size() / pango.SCALE

        self.labels = graphics.Sprite()

        self.date_label = graphics.Label(size = self.default_size)

        self.interval_label = graphics.Label(size = self.default_size)
        self.labels.add_child(self.interval_label)

        self.activity_label = graphics.Label(size = self.default_size)
        self.labels.add_child(self.activity_label)

        self.category_label = graphics.Label(size = self.default_size)
        self.labels.add_child(self.category_label)

        self.description_label = graphics.Label(size = self.default_size)
        self.labels.add_child(self.description_label)

        self.duration_label = graphics.Label(size=self.default_size)
        self.labels.add_child(self.duration_label)

        default_font = gtk.Style().font_desc.to_string()

        self.tag = Tag("")

        self.selected_color = None
        self.normal_color = None

        self.col_padding = 10
        self.row_padding = 4

    def do_set_property (self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr (self, pspec.name)


    def on_render (self, window, widget, background_area, cell_area, expose_area, flags):
        if not self.data:
            return

        """
          ASCII Art
          --------------+--------------------------------------------+-------+---+
          13:12 - 17:18 | Some activity - category  tag, tag, tag,   | 14:44 | E |
                        | tag, tag, some description                 |       |   |
          --------------+--------------------------------------------+-------+---+
        """
        # set the colors
        self.selected_color = widget.get_style().text[gtk.STATE_SELECTED]
        self.normal_color = widget.get_style().text[gtk.STATE_NORMAL]

        context = window.cairo_create()

        if isinstance(self.data, FactRow):
            fact, parent = self.data, None
        else:
            parent, fact = self.data, None


        x, y, width, height = cell_area
        context.translate(x, y)

        if flags & gtk.CELL_RENDERER_SELECTED:
            text_color = self.selected_color
        else:
            text_color = self.normal_color

        self.date_label.color = text_color
        self.duration_label.color = text_color

        if parent:
            self.date_label.text = "<b>%s</b>" % stuff.escape_pango(parent.label)
            self.date_label.x = 5

            if self.data.first:
                y = 5
            else:
                y = 20

            self.date_label.y = y


            self.duration_label.text = "<b>%s</b>" % stuff.format_duration(parent.duration)
            self.duration_label.x = width - self.duration_label.width
            self.duration_label.y = y

            self.date_label._draw(context)
            self.duration_label._draw(context)
        else:
            self.render_cell(context, (x,y,width,height), widget, flags)


    def render_cell(self, context, bounds, widget, flags, really = True):
        if not bounds:
            return -1
        x, y, cell_width, h = bounds

        self.selected_color = widget.get_style().text[gtk.STATE_SELECTED]
        self.normal_color = widget.get_style().text[gtk.STATE_NORMAL]

        g = graphics.Graphics(context)

        fact = self.data

        selected = flags and flags & gtk.CELL_RENDERER_SELECTED

        text_color = self.normal_color
        if selected:
            text_color = self.selected_color



        """ start time and end time at beginning of column """
        interval = fact.start_time.strftime("%H:%M -")
        if fact.end_time:
            interval = "%s %s" % (interval, fact.end_time.strftime("%H:%M"))

        self.interval_label.text = interval
        self.interval_label.color = text_color
        self.interval_label.x = self.col_padding
        self.interval_label.y = 2


        """ duration at the end """
        self.duration_label.text = stuff.format_duration(fact.delta)
        self.duration_label.color = text_color
        self.duration_label.x = cell_width - self.duration_label.width
        self.duration_label.y = 2


        """ activity, category, tags, description in middle """
        # we want our columns look aligned, so we will do fixed offset from
        # both sides, in letter length

        cell_start = widget.longest_interval
        cell_width = cell_width - widget.longest_interval - widget.longest_duration


        # align activity and category (ellipsize activity if it does not fit)
        category_width = 0

        self.category_label.text = ""
        if fact.category:
            self.category_label.text = " - <small>%s</small>" % stuff.escape_pango(fact.category)
            if not selected:
                category_color = graphics.Colors.contrast(text_color,  100)

                self.category_label.color = category_color
            else:
                self.category_label.color = text_color
            category_width = self.category_label.width


        self.activity_label.color = text_color
        self.activity_label.width = None
        self.activity_label.text = stuff.escape_pango(fact.name)

        # if activity label does not fit, we will shrink it
        if self.activity_label.width > cell_width - category_width:
            self.activity_label.width = (cell_width - category_width - self.col_padding)
            self.activity_label.ellipsize = pango.ELLIPSIZE_END
        else:
            self.activity_label.width = None
            #self.activity_label.ellipsize = None

        activity_width = self.activity_label.width

        y = 2

        self.activity_label.x = cell_start
        self.activity_label.y = y


        self.category_label.x = cell_start + activity_width
        self.category_label.y = y


        x = cell_start + activity_width + category_width + 12

        current_height = 0
        if fact.tags:
            # try putting tags on same line if they fit
            # otherwise move to the next line
            tags_end = cell_start + cell_width

            if x + self.tag.width > tags_end:
                x = cell_start
                y = self.activity_label.height + 4


            for i, tag in enumerate(fact.tags):
                self.tag.text = tag

                if x + self.tag.width >= tags_end:
                    x = cell_start
                    y += self.tag.height + 4

                self.tag.x, self.tag.y = x, y
                if really:
                    self.tag._draw(context)

                x += self.tag.width + 4

            current_height = y + self.tag.height + 4


        current_height = max(self.activity_label.height + 2, current_height)


        # see if we can fit in single line
        # if not, put description under activity
        self.description_label.text = ""
        if fact.description:
            self.description_label.text = "<small>%s</small>" % stuff.escape_pango(fact.description)
            self.description_label.color = text_color
            self.description_label.wrap = pango.WRAP_WORD

            description_width = self.description_label.width
            width = cell_width - x

            if description_width > width:
                x = cell_start
                y = current_height
                self.description_label.width = cell_width
            else:
                self.description_label.width = None

            self.description_label.x = x
            self.description_label.y = y

            current_height = max(current_height, self.description_label.y + self.description_label.height + 5)

        self.labels._draw(context)

        return current_height


    def on_get_size(self, widget, cell_area):
        if isinstance(self.data, GroupRow):
            if self.data.first:
                return (0, 0, 0, int((self.default_size + 10) * 1.5))
            else:
                return (0, 0, 0, (self.default_size + 10) * 2)


        context = gtk.gdk.CairoContext(cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0)))
        area = widget.get_allocation()

        area.width -= 40 # minus the edit column, scrollbar and padding (and the scrollbar part is quite lame)

        cell_height = self.render_cell(context, area, widget, None, False)
        return (0, 0, -1, cell_height)
