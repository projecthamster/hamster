# -*- coding: utf-8 -*-

# Copyright (C) 2007-2009 Toms Bauģis <toms.baugis at gmail.com>

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
import re
from lib import rt, stuff
from lib.rt import TICKET_NAME_REGEX
from hamster import widgets
from configuration import conf
from itertools import groupby
from collections import defaultdict
import logging

from configuration import load_ui_file


class ExportRow(object):
    def __init__(self, fact):
        self.fact = fact
        match = re.match(TICKET_NAME_REGEX, fact.activity)
        self.id = match.group(1)
        self.comment = self.get_text(fact)
        self.time_worked = stuff.duration_minutes(fact.delta)

    def __eq__(self, other):
        return isinstance(other, ExportRow) and other.id == self.id \
           and other.comment == self.comment \
           and other.time_worked == self.time_worked \
           and other.fact.start_time == self.fact.start_time \
           and other.fact.end_time == self.fact.end_time

    def get_text(self, fact):
        text = "%s, %s-%s" % (fact.date, fact.start_time.strftime("%H:%M"), fact.end_time.strftime("%H:%M"))
        if fact.description:
            text += ": %s" % (fact.description)
        if fact.tags:
            text += " ("+", ".join(fact.tags)+")"
        return text

    def __hash__(self):
        return self.id
    
class TicketRow(object):
    def __init__(self, ticket):
        self.ticket = ticket
        self.id = ticket['id']
        self.name = ticket['Subject']

    def __eq__(self, other):
        return isinstance(other, TicketRow) and other.id == self.id \
           and other.name == self.name

    def __hash__(self):
        return self.id
    
def id_painter(column, cell, model, iter):
    row = model.get_value(iter, 0)
    if isinstance(row, ExportRow):
        cell.set_visible(False)
    else:
        cell.set_visible(True)
        cell.set_property('text', row.id)


def name_comment_painter(column, cell, model, iter):
    row = model.get_value(iter, 0)
    if isinstance(row, ExportRow):
        cell.set_property('editable', True)
        cell.set_property('text', row.comment)
    else:
        cell.set_property('editable', False)
        cell.set_property('text', row.name)


def time_painter(column, cell, model, iter):
    row = model.get_value(iter, 0)
    if isinstance(row, ExportRow):
        cell.set_visible(True)
        adjustment = gtk.Adjustment(row.time_worked, 0, 1000, 1, 10, 0)
        cell.set_property("editable", True)
        cell.set_property("adjustment", adjustment)
        cell.set_property("text", row.time_worked)
    else:
        cell.set_visible(True)
        
        child_iter = model.iter_children(iter)
        time_worked = 0
        while child_iter:
            time_worked += model.get_value(child_iter, 0).time_worked
            child_iter = model.iter_next(child_iter)
            
        cell.set_property("editable", False)
        cell.set_property("adjustment", None)
        cell.set_property("text", time_worked)

class ExportRtController(gtk.Object):
    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, parent = None, facts = None):
        gtk.Object.__init__(self)
        
#        Init RT
        self.rt_url = conf.get("rt_url")
        self.rt_user = conf.get("rt_user")
        self.rt_pass = conf.get("rt_pass")
        self.tracker = rt.Rt(self.rt_url, self.rt_user, self.rt_pass)
        if not self.tracker.login():
            self.tracker = None

        self._gui = load_ui_file("export_rt.ui")
        self.window = self.get_widget('report_rt_window')

        self.parent, self.facts = parent, facts

        self.done_button = self.get_widget("done_button")
#        self.done_button.set_sensitive(False)
        
#        Model
        self.tree_store = gtk.TreeStore(gobject.TYPE_PYOBJECT)
        self.rows = [ExportRow(fact) for fact in facts]
        tickets = defaultdict(list)
        for ticket, rows in groupby(self.rows, lambda export_row: export_row.id):
            tickets[ticket] = list(rows)
        for item in tickets.keys():
            #ściągnąć nazwę ticketa
            ticket = self.tracker.get_ticket(item);
            parent = self.tree_store.append( None, (TicketRow(ticket), ) )
            for row in tickets[item]:
                self.tree_store.append(parent, (row, ))
            
#        self.tree_store.append(parent, (row.comment))
        self.view = gtk.TreeView(self.tree_store);
        
        
        id_cell = gtk.CellRendererText()
        id_column = gtk.TreeViewColumn("", id_cell, text=0)
        id_column.set_cell_data_func(id_cell, id_painter)
        id_column.set_max_width(100)
        self.view.append_column(id_column)
        
        name_comment_cell = gtk.CellRendererText()
        name_comment_cell.connect("edited", self.on_comment_edited)
        name_comment_column = gtk.TreeViewColumn("", name_comment_cell, text=0)
        name_comment_column.set_cell_data_func(name_comment_cell, name_comment_painter)
        name_comment_column.set_expand(True)
        self.view.append_column(name_comment_column)
        
        time_cell = gtk.CellRendererSpin()
        time_cell.connect("edited", self.on_time_worked_edited)
        time_column = gtk.TreeViewColumn("", time_cell, text=0)
        time_column.set_cell_data_func(time_cell, time_painter)
        time_column.set_min_width(60)
        self.view.append_column(time_column)
        self.view.expand_all()
        
        self.get_widget("activities").add(self.view)

        self._gui.connect_signals(self)

        self.window.show_all()
    
    
    def on_time_worked_edited(self, widget, path, value):
        row = self.tree_store[path][0]
        row.time_worked = int(value)
        
    def on_comment_edited(self, widget, path, value):
        row = self.tree_store[path][0]
        row.comment = value

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def show(self):
        self.window.show()
        
    def on_start_activate(self, button):
        if self.tracker:
            for fact in self.facts:
                match = re.match(TICKET_NAME_REGEX, fact.activity)
                if fact.end_time and match:
                    ticket_id = match.group(1)
                    text = self.get_text(fact)
                    time_worked = stuff.duration_minutes(fact.delta)
                    logging.warn(ticket_id)
                    logging.warn(text)
                    logging.warn("minutes: %s" % time_worked)
#                    external.tracker.comment(ticket_id, text, time_worked)
                else:
                    logging.warn("Not a RT ticket or in progress: %s" % fact.activity)
        else:
            logging.warn("Not connected to/logged in RT")

    def get_text(self, fact):
        text = "%s, %s-%s" % (fact.date, fact.start_time.strftime("%H:%M"), fact.end_time.strftime("%H:%M"))
        if fact.description:
            text += ": %s" % (fact.description)
        if fact.tags:
            text += " ("+", ".join(fact.tags)+")"
        return text

    def on_window_key_pressed(self, tree, event_key):
        popups = self.start_date.popup.get_property("visible") or \
                 self.start_time.popup.get_property("visible") or \
                 self.end_time.popup.get_property("visible") or \
                 self.new_name.popup.get_property("visible") or \
                 self.new_tags.popup.get_property("visible")

        if (event_key.keyval == gtk.keysyms.Escape or \
           (event_key.keyval == gtk.keysyms.w and event_key.state & gtk.gdk.CONTROL_MASK)):
            if popups:
                return False

            self.close_window()

        elif event_key.keyval in (gtk.keysyms.Return, gtk.keysyms.KP_Enter):
            if popups:
                return False
            self.on_save_button_clicked(None)

    def on_done_activate(self, button):
        self.on_close(button, None)

    def on_close(self, widget, event):
        self.tracker.logout();
        self.close_window()

    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            self.window = None
            self._gui = None
            self.emit("on-close")

    def show_facts(self):
        self.view.detach_model()
        for fact in self.facts:
            self.view.add_fact(fact)
        self.view.attach_model()
        