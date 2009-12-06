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
    cell_text = model.get_value(iter, 1)
    
    if model.get_value(iter, 6) is None:
        if model.get_path(iter) == (0,):
            text = '<span weight="heavy">%s</span>' % cell_text
        else:
            text = '<span weight="heavy" rise="-20000">%s</span>' % cell_text
            
        cell.set_property('markup', text)

    else:
        activity_name = stuff.escape_pango(cell_text)
        description = stuff.escape_pango(model.get_value(iter, 4))
        category = stuff.escape_pango(model.get_value(iter, 5))

        markup = stuff.format_activity(activity_name,
                                       category,
                                       description,
                                       pad_description = True)            
        cell.set_property('markup', markup)

def duration_painter(column, cell, model, iter):
    cell.set_property('xalign', 1)


    text = model.get_value(iter, 2)
    if model.get_value(iter, 6) is None:
        if model.get_path(iter) == (0,):
            text = '<span weight="heavy">%s</span>' % text
        else:
            text = '<span weight="heavy" rise="-20000">%s</span>' % text
    cell.set_property('markup', text)

def action_painter(column, cell, model, iter):
    cell.set_property('xalign', 1)


    text = model.get_value(iter, 2)
    if model.get_value(iter, 6) is None:
        cell.set_property("stock_id", "")
    else:
        cell.set_property("stock_id", "gtk-edit")


class FactTree(gtk.TreeView):
    def __init__(self):
        gtk.TreeView.__init__(self)
        
        self.set_headers_visible(False)
        self.set_show_expanders(False)

        #id, caption, duration, date (invisible), description, category
        self.set_model(gtk.TreeStore(int, str, str, str, str, str, gobject.TYPE_PYOBJECT))


        # name
        nameColumn = gtk.TreeViewColumn()
        nameCell = gtk.CellRendererText()
        #nameCell.set_property("ellipsize", pango.ELLIPSIZE_END)
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_cell_data_func(nameCell, parent_painter)
        self.append_column(nameColumn)

        tag_cell = TagCellRenderer()
        tag_cell.font_size = 8;
        tagColumn = gtk.TreeViewColumn("", tag_cell, data=6)
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


        self.show()
    
    def clear(self):
        self.model.clear()
        
    @property
    def model(self):
        return self.get_model()
        
    def add_fact(self, fact, parent = None):
        duration = stuff.duration_minutes(fact["delta"]) / 60

        if fact["end_time"]:
            fact_time = "%s - %s " % (fact["start_time"].strftime("%H:%M"),
                                   fact["end_time"].strftime("%H:%M"))
        else:
            fact_time = fact["start_time"].strftime("%H:%M ")

        self.model.append(parent, [fact["id"],
                                   "%s %s" % (fact_time, fact["name"]),
                                   stuff.format_duration(fact["delta"]),
                                   fact["start_time"].strftime('%Y-%m-%d'),
                                   fact["description"],
                                   fact["category"],
                                   fact])

    def add_group(self, group_label, facts):
        total = sum([stuff.duration_minutes(fact["delta"]) for fact in facts])
        
        # adds group of facts with the given label
        group_row = self.model.append(None,
                                    [-1,
                                     group_label,
                                     stuff.format_duration(total),
                                     "",
                                     "",
                                     "",
                                     None])
        
        for fact in facts:
            self.add_fact(fact, group_row)

        self.expand_all()

