# - coding: utf-8 -

# Copyright (C) 2008-2010 Toms Bauģis <toms.baugis at gmail.com>

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

import webbrowser

from itertools import groupby
from gettext import ngettext

import datetime as dt
import calendar
import time
from collections import defaultdict

import widgets
from configuration import runtime, dialogs
from lib import stuff, trophies
from lib.i18n import C_


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


    def search(self, start_date, end_date, facts):
        self.start_date = start_date
        self.end_date = end_date
        self.facts = facts
        self.fill_facts_tree()


    def fill_facts_tree(self):
        dates = defaultdict(list)

        # fill blanks
        for i in range((self.end_date - self.start_date).days + 1):
            dates[self.start_date + dt.timedelta(i)] = []

        #update with facts for the day
        for date, facts in groupby(self.facts, lambda fact: fact.date):
            dates[date] = list(facts)


        # detach model to trigger selection memory and speeding up
        self.fact_tree.detach_model()

        # push facts in tree
        for date, facts in sorted(dates.items(), key=lambda t: t[0]):
            fact_date = date.strftime(C_("overview list", "%A, %b %d"))
            self.fact_tree.add_group(fact_date, date, facts)

        self.fact_tree.attach_model()


    def delete_selected(self):
        fact = self.fact_tree.get_selected_fact()
        if not fact or isinstance(fact, dt.date):
            return

        runtime.storage.remove_fact(fact.id)

    def copy_selected(self):
        fact = self.fact_tree.get_selected_fact()

        if isinstance(fact, dt.date):
            return # heading

        fact_str = "%s-%s %s" % (fact.start_time.strftime("%H:%M"),
                               (fact.end_time or dt.datetime.now()).strftime("%H:%M"),
                               fact["name"])

        if fact.category:
            fact_str += "@%s" % fact.category

        if fact.description or fact.tags:
            tag_str = " ".join("#%s" % tag for tag in fact.tags)
            fact_str += ", %s" % ("%s %s" % (fact.description or "", tag_str)).strip()

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
            dialogs.edit.show(self, fact_id = fact_or_date.id)


    def on_facts_keys(self, tree, event):
        if (event.keyval == gtk.keysyms.Delete):
            self.delete_selected()
            return True
        elif (event.keyval == gtk.keysyms.Insert):
            self.launch_edit(self.fact_tree.get_selected_fact())
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
        fact = self.fact_tree.get_selected_fact()

        if not fact:
            return

        if isinstance(fact, dt.date):
            selected_date = fact
        else:
            selected_date = fact.date

        fact = stuff.Fact(text.decode("utf-8"))

        if not all((fact.activity, fact.start_time, fact.end_time)):
            return

        fact.start_time = fact.start_time.replace(year = selected_date.year,
                                                  month = selected_date.month,
                                                  day = selected_date.day)
        fact.end_time = fact.end_time.replace(year = selected_date.year,
                                              month = selected_date.month,
                                              day = selected_date.day)
        new_id = runtime.storage.add_fact(fact)

        # You can do that?! - copy/pasted an activity
        trophies.unlock("can_do_that")

        if new_id:
            self.fact_tree.select_fact(new_id)

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
