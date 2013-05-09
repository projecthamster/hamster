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
import logging
from itertools import groupby
import math

from lib import rt, stuff, redmine
from lib.rt import TICKET_NAME_REGEX
from configuration import conf, runtime, load_ui_file


class ExportRow(object):
    def __init__(self, fact):
        self.fact = fact
        match = re.match(TICKET_NAME_REGEX, fact.activity)
        self.id = match.group(1)
        self.comment = self.get_text(fact)
        self.date = self.get_date(fact)
        self.time_worked = stuff.duration_minutes(fact.delta)

    def __eq__(self, other):
        return isinstance(other, ExportRow) and other.id == self.id \
           and other.comment == self.comment \
           and other.time_worked == self.time_worked \
           and other.fact.start_time == self.fact.start_time \
           and other.fact.end_time == self.fact.end_time \
           and other.fact.id == self.fact.id

    def get_text(self, fact):
        text = "%s, %s-%s" % (fact.date, fact.start_time.strftime("%H:%M"), fact.end_time.strftime("%H:%M"))
        if fact.description:
            text += ": %s" % (fact.description)
        if fact.tags:
            text += " ("+", ".join(fact.tags)+")"
        return text
        
    def get_date(self, fact):
        date = fact.date.isoformat()
        return date

    def __hash__(self):
        
        return hash(self.id) \
            ^ hash(self.comment) \
            ^ hash(self.time_worked) \
            ^ hash(self.fact.start_time) \
            ^ hash(self.fact.end_time) \
            ^ hash(self.fact.id)
    
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
    
def id_painter(column, cell, model, it):
    row = model.get_value(it, 0)
    if isinstance(row, ExportRow):
        cell.set_visible(False)
        cell.set_property("weight-set", False)
    else:
        cell.set_visible(True)
        cell.set_property('text', row.id)
        cell.set_property("weight-set", True)
        cell.set_property("weight", 700)


def name_comment_painter(column, cell, model, it):
    row = model.get_value(it, 0)
    if isinstance(row, ExportRow):
        cell.set_property('editable', True)
        cell.set_property('text', stuff.escape_pango(row.comment))
        cell.set_property("weight-set", False)
    else:
        cell.set_property('editable', False)
        cell.set_property('text', row.name)
        cell.set_property("weight-set", True)
        cell.set_property("weight", 700)


def time_painter(column, cell, model, it):
    row = model.get_value(it, 0)
    if isinstance(row, ExportRow):
        cell.set_visible(True)
        adjustment = gtk.Adjustment(row.time_worked, -1000, 1000, 1, 10, 0)
        cell.set_property("editable", True)
        cell.set_property("adjustment", adjustment)
        cell.set_property("text", "%s min" % row.time_worked)
        cell.set_property("weight-set", False)
    else:
        cell.set_visible(True)
        
        child_iter = model.iter_children(it)
        time_worked = 0
        while child_iter:
            time_worked += model.get_value(child_iter, 0).time_worked
            child_iter = model.iter_next(child_iter)
            
        cell.set_property("editable", False)
        cell.set_property("adjustment", None)
        cell.set_property("text", "%s min" % time_worked)
        cell.set_property("weight-set", True)
        cell.set_property("weight", 700)

class ExportRtController(gtk.Object):
    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, parent = None, facts = None):
        gtk.Object.__init__(self)
        
        self.source = conf.get("activities_source")

        if self.source == "rt":
#            Init RT
            self.rt_url = conf.get("rt_url")
            self.rt_user = conf.get("rt_user")
            self.rt_pass = conf.get("rt_pass")

            self.tracker = rt.Rt(self.rt_url, self.rt_user, self.rt_pass)
            if not self.tracker.login():
                self.tracker = None
        elif self.source == "redmine":
            self.rt_url = conf.get("rt_url")
            self.rt_user = conf.get("rt_user")
            self.rt_pass = conf.get("rt_pass")

            if self.rt_url and self.rt_user and self.rt_pass:
                try:
                    self.tracker = redmine.Redmine(self.rt_url, auth=(self.rt_user,self.rt_pass))
                    if not self.tracker:
                        self.source = ""
                except:
                    self.source = ""
            else:
                self.source = ""
                
        self._gui = load_ui_file("export_rt.ui")
        self.window = self.get_widget('report_rt_window')

        self.parent, self.facts = parent, facts

        self.done_button = self.get_widget("done_button")
#        self.done_button.set_sensitive(False)
        
#        Model
        self.tree_store = gtk.TreeStore(gobject.TYPE_PYOBJECT)
        self.rows = list([ExportRow(fact) for fact in facts])
        self.rows.sort(key = lambda row: row.id)
        tickets = {}
        for ticket, rows in groupby(self.rows, lambda export_row: export_row.id):
            tickets[ticket] = list(rows)
        for item in tickets.keys():
            #ściągnąć nazwę ticketa
            if self.source == "rt":
                ticket = self.tracker.get_ticket(item);
            elif self.source == "redmine":
                issue = self.tracker.getIssue(item);
                ticket = {};
                ticket['id'] = issue.id
                ticket['Subject'] = issue.subject

            if ticket:
                parent = self.tree_store.append( None, (TicketRow(ticket), ) )
                for row in tickets[item]:
                    self.tree_store.append(parent, (row, ))
            
#        self.tree_store.append(parent, (row.comment))
        self.view = gtk.TreeView(self.tree_store);
        self.view.set_headers_visible(False)
        
        
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
        
        self.start_button = self.get_widget("start_button")
        self.get_widget("activities").add(self.view)
        self.aggregate_comments_checkbox = self.get_widget("aggregate_comments_checkbox")
        self.aggregate_comments_checkbox.set_active(True)
        self.test_checkox = self.get_widget("test_checkbox")
        self.test_checkox.set_active(False)
        self.progressbar = self.get_widget("progressbar")
        self.progressbar.set_text(_("Waiting for action"))
        self.progressbar.set_orientation(gtk.PROGRESS_LEFT_TO_RIGHT)
        
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
            group_comments = self.aggregate_comments_checkbox.get_active()
            it = self.tree_store.get_iter_first()
            to_report_list = []
            while it:
                ticket_row = self.tree_store.get_value(it, 0)
                child_iter = self.tree_store.iter_children(it)
                #get childs
                export_rows = []
                while child_iter:
                    export_rows.append(self.tree_store.get_value(child_iter, 0))
                    child_iter = self.tree_store.iter_next(child_iter)
                #report tickets
                if group_comments:
                    comment = "\n".join("%s - %s min"% (row.comment, row.time_worked) for row in export_rows)
                    time_worked = sum([row.time_worked for row in export_rows])
                    facts = [row.fact for row in export_rows]
                    to_report_list.append({'id':ticket_row.id, 'name':ticket_row.name, 'comment':comment, 'time':time_worked, 'facts':facts, 'date': row.date})
                else:
                    for row in export_rows:
                        to_report_list.append({'id':ticket_row.id, 'name':ticket_row.name, 'comment':"%s - %s min"% (row.comment, row.time_worked), 'time':row.time_worked, 'facts':[row.fact], 'date': row.date})
#                        self.__comment_ticket(ticket_row.id, "%s - %s min"% (row.comment, row.time_worked), row.time_worked, [row.fact])
                it = self.tree_store.iter_next(it)
            to_report_len = len(to_report_list)
            self.progressbar.set_fraction(0.0)
            for i in range(to_report_len):
                to_report = to_report_list[i]
                self.progressbar.set_text(_("Reporting: #%s: %s - %smin") % (to_report['id'], to_report['name'], to_report['time']))
                self.progressbar.set_fraction(float(i)/to_report_len)
                while gtk.events_pending(): 
                    gtk.main_iteration()
                if self.source == "rt":
                    self.__comment_ticket(to_report['id'], to_report['comment'], to_report['time'], to_report['facts'])
                elif self.source == "redmine":
                    self.__add_time_entry(to_report['id'], to_report['date'], math.ceil(to_report['time']*100/60)/100, to_report['comment'], to_report['facts'])
            self.progressbar.set_text("Done")
            self.progressbar.set_fraction(1.0)
#            for fact in self.facts:
#                match = re.match(TICKET_NAME_REGEX, fact.activity)
#                if fact.end_time and match:
#                    ticket_id = match.group(1)
#                    text = self.get_text(fact)
#                    time_worked = stuff.duration_minutes(fact.delta)
#                    logging.warn(ticket_id)
#                    logging.warn(text)
#                    logging.warn("minutes: %s" % time_worked)
##                    external.tracker.comment(ticket_id, text, time_worked)
#                else:
#                    logging.warn("Not a RT ticket or in progress: %s" % fact.activity)
        else:
            logging.warn(_("Not connected to/logged in RT"))
        self.start_button.set_sensitive(False)
        #TODO only if parent is overview
        self.parent.search()
            
    def __comment_ticket(self, ticket_id, text, time_worked, facts):
        test = self.test_checkox.get_active()
#        logging.warn(_("updating ticket #%s: %s min, comment: \n%s") % (ticket_id, time_worked, text))
        if not test:
            time = time_worked
        else:
            time = 0

        if self.tracker.comment(ticket_id, text, time) and not test:
            for fact in facts:
                runtime.storage.update_fact(fact.id, fact, False,True)
                fact_row.selected = False
            
    def __add_time_entry(self, issue_id, spent_on, hours, comments, facts):
        test = self.test_checkox.get_active()
        logging.warn(_("updating issue #%s: %s hrs, comment: \n%s") % (issue_id, hours, comments))
        time_entry_data = {'time_entry': {}}
        time_entry_data['time_entry']['issue_id'] = issue_id
        time_entry_data['time_entry']['spent_on'] = spent_on
        time_entry_data['time_entry']['hours'] = hours
        time_entry_data['time_entry']['comments'] = comments
        time_entry_data['time_entry']['activity_id'] = 9
        
        r = self.tracker.createTimeEntry(time_entry_data)
        logging.warn(r.status_code)
        logging.warn(r.content)
        if r.status_code == 201 and not test:
            for fact in facts:
                runtime.storage.update_fact(fact.id, fact, False,True)
#                fact_row.selected = False

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
        if self.source == "rt":
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
        
