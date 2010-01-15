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
from tags import TagCellRenderer

import pango

def parent_painter(column, cell, model, iter):
    fact = model.get_value(iter, 0)
    parent_info = model.get_value(iter, 2)

    if fact is None:
        if model.get_path(iter) == (0,):  # first row
            text = '<span weight="heavy">%s</span>' % parent_info["label"]
        else:
            text = '<span weight="heavy" rise="-20000">%s</span>' % parent_info["label"]

        cell.set_property('markup', text)

    else:
        if fact["end_time"]:
            fact_time = "%s - %s " % (fact["start_time"].strftime("%H:%M"),
                                   fact["end_time"].strftime("%H:%M"))
        else:
            fact_time = fact["start_time"].strftime("%H:%M ")
        

        activity_name = stuff.escape_pango("%s %s" % (fact_time, fact["name"]))
        description = stuff.escape_pango(fact["description"])
        category = stuff.escape_pango(fact["category"])

        markup = stuff.format_activity(activity_name,
                                       category,
                                       description,
                                       pad_description = True)
        cell.set_property('markup', markup)

def duration_painter(column, cell, model, iter):
    cell.set_property('xalign', 1)


    text = model.get_value(iter, 1)
    if model.get_value(iter, 0) is None:
        if model.get_path(iter) == (0,):
            text = '<span weight="heavy">%s</span>' % text
        else:
            text = '<span weight="heavy" rise="-20000">%s</span>' % text
    cell.set_property('markup', text)

def action_painter(column, cell, model, iter):
    cell.set_property('xalign', 1)

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
        self.store_model = gtk.TreeStore(gobject.TYPE_PYOBJECT, str, gobject.TYPE_PYOBJECT)
        self.set_model(self.store_model)


        # start time - end time, name, category
        nameColumn = gtk.TreeViewColumn()
        nameCell = gtk.CellRendererText()
        #nameCell.set_property("ellipsize", pango.ELLIPSIZE_END)
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_cell_data_func(nameCell, parent_painter)
        self.append_column(nameColumn)

        # tags
        tag_cell = TagCellRenderer()
        tag_cell.set_font_size(8);
        tagColumn = gtk.TreeViewColumn("", tag_cell, data=0)
        tagColumn.set_expand(True)
        self.append_column(tagColumn)


        # duration
        timeColumn = gtk.TreeViewColumn()
        timeCell = gtk.CellRendererText()
        timeColumn.pack_end(timeCell, True)
        timeColumn.set_cell_data_func(timeCell, duration_painter)
        self.append_column(timeColumn)

        edit_cell = gtk.CellRendererPixbuf()
        edit_cell.set_property("mode", gtk.CELL_RENDERER_MODE_ACTIVATABLE)
        self.edit_column = gtk.TreeViewColumn("", edit_cell)
        self.edit_column.set_cell_data_func(edit_cell, action_painter)
        self.append_column(self.edit_column)

        self.connect("row-activated", self._on_row_activated)
        self.connect("button-release-event", self._on_button_release_event)
        self.connect("key-press-event", self._on_key_pressed)

        self.show()
        
        self.stored_selection = None

    def clear(self):
        self.store_model.clear()

    def add_fact(self, fact, parent = None):
        duration = stuff.duration_minutes(fact["delta"]) / 60

        if fact["end_time"]:
            fact_time = "%s - %s " % (fact["start_time"].strftime("%H:%M"),
                                   fact["end_time"].strftime("%H:%M"))
        else:
            fact_time = fact["start_time"].strftime("%H:%M ")

        self.store_model.append(parent, [fact,
                                         stuff.format_duration(fact["delta"]),
                                         None])

    def add_group(self, group_label, group_date, facts):
        total = sum([stuff.duration_minutes(fact["delta"]) for fact in facts])

        # adds group of facts with the given label
        group_row = self.store_model.append(None, [None,
                                                   stuff.format_duration(total),
                                                   dict(date = group_date,
                                                        label = group_label)])

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
            return model[iter][0] or model[iter][2]["date"]
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
