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
        self.store_model = gtk.TreeStore(gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)
        self.set_model(self.store_model)


        fact_cell = FactCellRenderer()
        fact_column = gtk.TreeViewColumn("", fact_cell, data=0)
        fact_column.set_cell_data_func(fact_cell, parent_painter)
        fact_column.set_expand(True)
        self.append_column(fact_column)

        edit_cell = gtk.CellRendererPixbuf()
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
        
        
        self.stored_selection = None

        self.box = None
        
        
    def fix_row_heights(self):
        alloc = self.get_allocation()
        if alloc != self.box:
            self.box = alloc
            self.columns_autosize()
        
    def clear(self):
        self.store_model.clear()
        self.longest_activity_category = 0

    def add_fact(self, fact, parent = None):
        self.longest_activity_category = max(self.longest_activity_category,
                                             len(fact["name"]) + len(fact["category"]))

        self.store_model.append(parent, [fact, None])

    def add_group(self, group_label, group_date, facts):
        total = sum([stuff.duration_minutes(fact["delta"]) for fact in facts])

        # adds group of facts with the given label
        group_row = self.store_model.append(None, [None,
                                                   dict(date = group_date,
                                                        label = group_label,
                                                        duration = total)])

        for fact in facts:
            self.add_fact(fact, group_row)

        self.expand_all()

    def detach_model(self):
        # ooh, somebody is going for refresh!
        # let's save selection too - maybe it will come handy
        selection = self.get_selection()
        self.stored_selection = selection.get_selected_rows()[1]
        
        self.set_model()

    def attach_model(self):
        self.set_model(self.store_model)
        self.expand_all()
        
        if self.stored_selection:
            selection = self.get_selection()
            selection.select_path(self.stored_selection[0])

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

        self.layout = None
        
        self.col_padding = 10
        self.row_padding = 4
        
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

            self.layout.set_markup("<b>%s</b>" % parent["label"])
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
               
            
            """ start time and end time at beginning of column """
            interval = fact["start_time"].strftime("%H:%M")
            if fact["end_time"]:
                interval = "%s - %s" % (interval, fact["end_time"].strftime("%H:%M"))
            
            self.set_color(context, text_color)

            self.layout.set_markup(interval)
            context.move_to(self.col_padding, 2)
            context.show_layout(self.layout)

            """ duration at the end """
            self.layout.set_markup(stuff.format_duration(fact["delta"]))
            duration_w, duration_h = self.layout.get_pixel_size()
            context.move_to(width - duration_w, 2)
            context.show_layout(self.layout)
            
            """ activity, category, tags, description in middle """
            # we want our columns look aligned, so we will do fixed offset from
            # both sides, in letter length
            self.layout.set_markup("8")
            letter_w, letter_h = self.layout.get_pixel_size()
            
            box_x = letter_w * 14
            box_w = width - letter_w * 15 - max(letter_w * 10, duration_w)

            context.translate(box_x, 2)

            context.move_to(0,0)
            self.layout.set_markup(fact["name"])
            label_w, label_h = self.layout.get_pixel_size()
            self.set_color(context, text_color)
            context.show_layout(self.layout)

            context.move_to(label_w, 0)

            if not selected:
                self.set_color(context, widget.get_style().text[gtk.STATE_INSENSITIVE])
            self.layout.set_markup(" - %s" % fact["category"])
            label_w, label_h = self.layout.get_pixel_size()
            context.show_layout(self.layout)
            
            act_cat_offset = (widget.longest_activity_category + 4) * letter_w
            context.move_to(act_cat_offset, 0)
            context.set_source_rgb(0,0,0)
            
            self.layout.set_font_description(self.tag_font)
            cur_x, cur_y = act_cat_offset, 0
            for i, tag in enumerate(fact["tags"]):
                tag_w, tag_h = Tag.tag_size(tag, self.layout)
                
                if i > 0 and cur_x + tag_w >= box_w:
                    cur_x = act_cat_offset
                    cur_y += tag_h + 4
                
                Tag(context, self.layout, True, tag, None,
                    gtk.gdk.Rectangle(cur_x, cur_y, box_w - cur_x, height - cur_y))
                
                cur_x += tag_w + 4

            self.layout.set_font_description(self.label_font)

            if fact["description"]:
                self.layout.set_markup("<small><i>%s</i></small>" % fact["description"])
                label_w, label_h = self.layout.get_pixel_size()
                
                x, y = cur_x, cur_y + 4
                if cur_x + label_w > box_w:
                    x = 0
                    y = label_h + 4
                
                context.move_to(x, y)
                self.layout.set_width((box_w - x) * pango.SCALE)
                context.show_layout(self.layout)
                self.layout.set_width(-1)
                
            self.layout.set_font_description(self.label_font)


    def set_color(self, context, color):
        context.set_source_rgba(*self.color_to_cairo_rgba(color))
        
    def color_to_cairo_rgba(self, c, a=1):
        return c.red/65535.0, c.green/65535.0, c.blue/65535.0, a


    def get_fact_size(self, widget):
        #all we care for, is height
        if not self.data or "id" not in self.data:
            return None
        fact = self.data

        pixmap = gtk.gdk.Pixmap(None, 10, 10, 24)
        context = pixmap.cairo_create()

        layout = context.create_layout()
        layout.set_font_description(self.label_font)


        x, y, width, height = widget.get_allocation()


        """ duration at the end """
        layout.set_markup(stuff.format_duration(fact["delta"]))
        duration_w, duration_h = layout.get_pixel_size()
        
        """ activity, category, tags, description in middle """
        # we want our columns look aligned, so we will do fixed offset from
        # both sides, in letter length
        layout.set_markup("8")
        letter_w, letter_h = layout.get_pixel_size()
        
        box_x = letter_w * 14
        box_w = width - letter_w * 15 - max(letter_w * 14, duration_w)

        act_cat_offset = (widget.longest_activity_category + 4) * letter_w

        required_height = letter_h

        if fact["tags"]:
            layout.set_font_description(self.tag_font)
            cur_x, cur_y = act_cat_offset, 0
            for i, tag in enumerate(fact["tags"]):
                tag_w, tag_h = Tag.tag_size(tag, layout)
                
                if i > 0 and cur_x + tag_w >= box_w:
                    cur_x = act_cat_offset
                    cur_y += tag_h + 4
                
                cur_x += tag_w + 4
            
            required_height = cur_y + tag_h + 4

        layout.set_font_description(self.label_font)

        if fact["description"]:
            layout.set_markup("<small><i>%s</i></small>" % fact["description"])
            label_w, label_h = layout.get_pixel_size()
            
            x, y = cur_x, cur_y + 4
            if cur_x + label_w > box_w:
                x = 0
                y = label_h + 4
            
            layout.set_width((box_w - x) * pango.SCALE)
            label_w, label_h = layout.get_pixel_size()


            required_height = y + label_h

        required_height = required_height + 6
        return (0, 0, 0, required_height)


    def on_get_size (self, widget, cell_area = None):
        if "id" in self.data: # fact
            return self.get_fact_size(widget)
        else:
            if self.data["first"]:
                return (0, 0, 0, 25)
            else:
                return (0, 0, 0, 40)
            


