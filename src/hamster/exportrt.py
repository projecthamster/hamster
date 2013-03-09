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
from hamster import widgets
from configuration import conf
import logging

from configuration import load_ui_file

class ExportRtController(gtk.Object):
    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, parent = None, facts = None):
        gtk.Object.__init__(self)

        self._gui = load_ui_file("export_rt.ui")
        self.window = self.get_widget('report_rt_window')

        self.parent, self.facts = parent, facts

        #TODO - should somehow hint that time is not welcome here
        self.done_button = self.get_widget("done_button")
        self.done_button.set_sensitive(False)
        
        
        self.treeview = widgets.FactTree(True)
#        self.treeview.connect("key-press-event", self.on_todays_keys)
#        self.treeview.connect("edit-clicked", self._open_edit_activity)
#        self.treeview.connect("row-activated", self.on_today_row_activated)
        self.get_widget("activities").add(self.treeview)
        self.show_facts()
        
        
        self.rt_url = conf.get("rt_url")
        self.rt_user = conf.get("rt_user")
        self.rt_pass = conf.get("rt_pass")
        self.tracker = rt.Rt(self.rt_url, self.rt_user, self.rt_pass)
        if not self.tracker.login():
            self.tracker = None
        

        self._gui.connect_signals(self)

        self.window.show_all()

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def show(self):
        self.window.show()
        
    def on_start_activate(self, button):
        if self.tracker:
            for fact in self.facts:
                match = re.match("^#(\d+): ", fact.activity)
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
        text = "%s, %s - %s" % (fact.date, fact.start_time.strftime("%H:%M"), fact.end_time.strftime("%H:%M"))
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
        pass

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
        self.treeview.detach_model()
        for fact in self.facts:
            self.treeview.add_fact(fact)
        self.treeview.attach_model()
        