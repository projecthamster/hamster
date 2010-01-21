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

import stuff

import widgets

from configuration import runtime, dialogs
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
        self.set_border_width(6)

        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scroll.set_shadow_type(gtk.SHADOW_IN)

        self.start_date, self.end_date = None, None
        self.facts = []

        self.fact_tree = widgets.FactTree()
        self.fact_tree.connect("row-activated", self.on_facts_row_activated)
        self.fact_tree.connect("key-press-event", self.on_facts_keys)
        self.fact_tree.connect("edit-clicked", lambda tree, fact: self.on_edit_clicked(fact))

        scroll.add(self.fact_tree)
        self.add(scroll)

        self.ignore_next_refresh = False


    def search(self, start_date, end_date, facts):
        if self.ignore_next_refresh: # avoid reloading when we are operating with the data
            self.ignore_next_refresh = False
            return

        self.start_date = start_date
        self.end_date = end_date
        self.facts = facts
        self.fill_facts_tree()


    def fill_facts_tree(self):
        #create list of all required dates
        dates = [(self.start_date + dt.timedelta(i), [])
                    for i in range((self.end_date - self.start_date).days  + 1)]

        #update with facts for the day
        for date, facts in groupby(self.facts, lambda fact: fact["date"]):
            dates[dates.index((date, []))] = (date, list(facts))


        # detach model to trigger selection memory and speeding up
        self.fact_tree.detach_model()
        self.fact_tree.clear()

        # push facts in tree
        for date, facts in dates:
            fact_date = date.strftime(C_("overview list", "%A, %b %d"))
            self.fact_tree.add_group(fact_date, date, facts)

        self.fact_tree.attach_model()


    def delete_selected(self):
        fact = self.fact_tree.get_selected_fact()
        if not fact or isinstance(fact, dt.date):
            return

        self.ignore_next_refresh = True

        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()
        self.fact_tree.select_next()

        model.remove(iter)
        runtime.storage.remove_fact(fact['id'])

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


    """ events """
    def on_edit_clicked(self, fact):
        self.launch_edit(fact)

    def on_facts_row_activated(self, tree, path, column):
        self.launch_edit(tree.get_selected_fact())

    def launch_edit(self, fact_or_date):
        if isinstance(fact_or_date, dt.date):
            dialogs.edit.show(self, fact_date = fact_or_date)
        else:
            dialogs.edit.show(self, fact_id = fact_or_date["id"])


    def on_facts_keys(self, tree, event):
        if (event.keyval == gtk.keysyms.Delete):
            self.delete_selected()
            return True
        elif (event.keyval == gtk.keysyms.Insert):
            dialogs.edit.show()
            return True
        elif event.keyval == gtk.keysyms.c and event.state & gtk.gdk.CONTROL_MASK:
            self.copy_selected()
            return True
        elif event.keyval == gtk.keysyms.v and event.state & gtk.gdk.CONTROL_MASK:
            self.check_clipboard()
            return True

        return False

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


if __name__ == "__main__":
    gtk.window_set_default_icon_name("hamster-applet")
    window = gtk.Window()
    window.set_title("Hamster - reports")
    window.set_size_request(800, 600)
    overview = OverviewBox()
    window.add(overview)
    window.connect("delete_event", lambda *args: gtk.main_quit())
    window.show_all()

    start_date = dt.date.today() - dt.timedelta(days=30)
    end_date = dt.date.today()
    facts = runtime.storage.get_facts(start_date, end_date)
    overview.search(start_date, end_date, facts)


    gtk.main()
