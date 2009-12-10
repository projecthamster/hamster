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


import pygtk
pygtk.require('2.0')

import os
import gtk, gobject
import pango

import stuff
import charting

from edit_activity import CustomFactController
import reports, graphics

import widgets

from configuration import runtime, GconfStore
import webbrowser

from itertools import groupby
from gettext import ngettext

import datetime as dt
import calendar
import time
from hamster.i18n import C_



class OverviewBox(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)
        self._gui = stuff.load_ui_file("stats_overview.ui")
        self.get_widget("overview_box").reparent(self) #mine!


        self.view_date = dt.date.today()
        #set to monday
        self.start_date = self.view_date - \
                                      dt.timedelta(self.view_date.weekday() + 1)
        # look if we need to start on sunday or monday
        self.start_date = self.start_date + \
                                      dt.timedelta(stuff.locale_first_weekday())
        
        self.end_date = self.start_date + dt.timedelta(6)

        self.fact_tree = widgets.FactTree()
        self.get_widget("overview_facts_box").add(self.fact_tree)
        self.fill_facts_tree()
        self.fact_tree.connect("cursor-changed", self.on_fact_selection_changed)
        self.fact_tree.connect("row-activated", self.on_facts_row_activated)
        self.fact_tree.connect("key-press-event", self.on_facts_keys)
        self.fact_tree.connect("edit_clicked", lambda tree, fact: self.on_edit_clicked(fact))

        self._gui.connect_signals(self)
        runtime.dispatcher.add_handler('activity_updated', self.after_activity_update)
        runtime.dispatcher.add_handler('day_updated', self.after_activity_update)

    def fill_facts_tree(self):
        facts = runtime.storage.get_facts(self.start_date, self.end_date)
        
        self.fact_tree.clear()
        
        #create list of all required dates
        dates = [(self.start_date + dt.timedelta(i), [])
                    for i in range((self.end_date - self.start_date).days  + 1)]
        
        #update with facts for the day
        for date, facts in groupby(facts, lambda fact: fact["date"]):
            dates[dates.index((date, []))] = (date, list(facts))

        # push them in tree
        for date, facts in dates:
            fact_date = date.strftime(C_("overview list", "%A, %b %d"))

            self.fact_tree.add_group(fact_date, facts)


    """ events """
    def after_activity_update(self, widget, renames):
        self.fill_facts_tree()

    def on_prev_clicked(self, button):
        self.start_date -= dt.timedelta(7)
        self.end_date -= dt.timedelta(7)
        self.fill_facts_tree()

    def on_next_clicked(self, button):
        self.start_date += dt.timedelta(7)
        self.end_date += dt.timedelta(7)        
        self.fill_facts_tree()
    
    def on_home_clicked(self, button):
        self.view_date = dt.date.today()

        self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
        self.start_date = self.start_date + dt.timedelta(stuff.locale_first_weekday())
        self.end_date = self.start_date + dt.timedelta(6)
        
        self.fill_facts_tree()


    def on_fact_selection_changed(self, tree):
        """ enables and disables action buttons depending on selected item """
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()

        id = -1
        if iter:
            id = model[iter][0]

        self.get_widget('remove').set_sensitive(id != -1)
        self.get_widget('edit').set_sensitive(id != -1)

        return True

    def on_facts_row_activated(self, tree, path, column):
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()
        custom_fact = CustomFactController(self, None, model[iter][0])
        custom_fact.show()
        

    def on_add_clicked(self, button):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        selected_date = self.view_date
        if iter:
            selected_date = model[iter][6]["date"]

        custom_fact = CustomFactController(self, selected_date)
        custom_fact.show()

    def on_remove_clicked(self, button):
        self.delete_selected()

    def on_facts_keys(self, tree, event):
        if (event.keyval == gtk.keysyms.Delete):
            self.delete_selected()
            return True
        
        return False

    def on_edit_clicked(self, button):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        if model[iter][0] == -1:
            return #not a fact

        custom_fact = CustomFactController(self, None, model[iter][0])
        custom_fact.show()

    def delete_selected(self):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        if model[iter][0] == -1:
            return #not a fact

        next_row = model.iter_next(iter)

        if next_row:
            selection.select_iter(next_row)
        else:
            path = model.get_path(iter)[0] - 1
            if path > 0:
                selection.select_path(path)

        runtime.storage.remove_fact(model[iter][0])

    def copy_selected(self):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        fact = model[iter][6]
        if not fact:
            return #not a fact

        fact_str = "%s-%s %s" % (fact["start_time"].strftime("%H:%M"),
                               (fact["end_time"] or dt.datetime.now()).strftime("%H:%M"),
                               fact["name"])

        if fact["category"]:
            fact_str += "@%s" % fact["category"]

        if fact["description"]:
            fact_str += ", %s" % fact["description"]

        clipboard = gtk.Clipboard()
        clipboard.set_text(fact_str)
    
    def check_clipboard(self):
        clipboard = gtk.Clipboard()
        clipboard.request_text(self.on_clipboard_text)
    
    def on_clipboard_text(self, clipboard, text, data):
        # first check that we have a date selected
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        selected_date = self.view_date
        if iter:
            selected_date = model[iter][3].split("-")
            selected_date = dt.date(int(selected_date[0]),
                                    int(selected_date[1]),
                                    int(selected_date[2]))
        if not selected_date:
            return
        
        res = stuff.parse_activity_input(text)

        if res.start_time is None or res.end_time is None:
            return
        
        start_time = res.start_time.replace(year = selected_date.year,
                                            month = selected_date.month,
                                            day = selected_date.day)
        end_time = res.end_time.replace(year = selected_date.year,
                                               month = selected_date.month,
                                               day = selected_date.day)
    
        activity_name = res.activity_name
        if res.category_name:
            activity_name += "@%s" % res.category_name
            
        if res.description:
            activity_name += ", %s" % res.description

        activity_name = activity_name.decode("utf-8")

        # TODO - set cursor to the pasted entry when done
        # TODO - revisit parsing of selected date
        added_fact = runtime.storage.add_fact(activity_name, start_time, end_time)
        

    """keyboard events"""
    def on_key_pressed(self, tree, event):
        if (event.keyval == gtk.keysyms.Delete):
            self.delete_selected()
        elif event.keyval == gtk.keysyms.c and event.state & gtk.gdk.CONTROL_MASK:
            self.copy_selected()
        elif event.keyval == gtk.keysyms.v and event.state & gtk.gdk.CONTROL_MASK:
            self.check_clipboard()
    

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)




if __name__ == "__main__":
    gtk.window_set_default_icon_name("hamster-applet")
    
    window = gtk.Window()
    window.set_title("Hamster - overview")
    window.set_size_request(800, 600)
    
    window.add(OverviewBox())

    window.show_all()    
    gtk.main()    
