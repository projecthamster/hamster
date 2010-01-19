#!/usr/bin/env python
# - coding: utf-8 -

# Copyright (C) 2009 Toms Bauģis <toms.baugis at gmail.com>

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

import logging
import datetime as dt

import pygtk
pygtk.require("2.0")
import gtk

from hamster.configuration import GConfStore, runtime
from hamster import widgets, stuff

import gobject

from hamster import graphics
import pango, cairo

class MainWindow(object):
    def __init__(self):
        self._gui = stuff.load_ui_file("hamster.ui")
        self.window = self._gui.get_object('main-window')
        self.gtk_main_quit = gtk.main_quit

        #TODO - replace with the tree background color (can't get it atm!)
        self.get_widget("todays_activities_ebox").modify_bg(gtk.STATE_NORMAL,
                gtk.gdk.Color(65536.0,65536.0,65536.0))

        self.new_name = widgets.ActivityEntry()
        widgets.add_hint(self.new_name, _("Time and Name"))
        self.get_widget("new_name_box").add(self.new_name)
        self.new_name.connect("changed", self.on_activity_text_changed)

        self.new_tags = widgets.TagsEntry()
        widgets.add_hint(self.new_tags, _("Tags or Description"))
        self.get_widget("new_tags_box").add(self.new_tags)

        self.tag_box = widgets.TagBox(interactive = False)
        self.get_widget("tag_box").add(self.tag_box)
        
        self.get_widget("tabs").set_current_page(1)

        self.set_last_activity()
        self.load_today()
        
        gtk.link_button_set_uri_hook(self.magic)
        

        runtime.dispatcher.add_handler('activity_updated', self.after_activity_update)
        runtime.dispatcher.add_handler('day_updated', self.after_fact_update)
        
        self._gui.connect_signals(self)
        
        

    def magic(self, button, uri):
        logging.debug('%s, %s' % (uri, button))
        

    def set_last_activity(self):
        activity = runtime.storage.get_last_activity()
        self.get_widget("stop_tracking").set_sensitive(activity != None)
        
        
        if activity:
            self.get_widget("switch_activity").show()
            self.get_widget("start_tracking").hide()
            
            delta = dt.datetime.now() - activity['start_time']
            duration = delta.seconds /  60
            
            self.get_widget("last_activity_duration").set_text(stuff.format_duration(duration) or _("Just started"))
            self.get_widget("last_activity_name").set_text(activity['name'])
            if activity['category'] != _("Unsorted"):
                self.get_widget("last_activity_category") \
                    .set_text(" - %s" % activity['category'])

            self.get_widget("last_activity_description").set_text(activity['description'])
            
            self.tag_box.draw(activity["tags"])
        else:
            self.get_widget("switch_activity").hide()
            self.get_widget("start_tracking").show()

            self.get_widget("last_activity_name").set_text(_("No activity"))
            self.get_widget("last_activity_duration").set_text("")
            self.get_widget("last_activity_category").set_text("")
            

    def load_today(self):
        todays_facts = runtime.storage.get_facts(dt.date.today())
        grid = self.get_widget("activities_today")
        
        #clear
        for child in grid.get_children(): grid.remove(child)
        

        def add_cell(cell, x, y, expandX = gtk.FILL,
                                 expandY = gtk.FILL):

            if isinstance(cell, str) or isinstance(cell, unicode):
                cell = gtk.Label(cell)
                cell.set_alignment(0.0, 0.0)
            
            grid.attach(cell, x, x + 1, y, y + 1, expandX, expandY)

            
        for rownum, fact in enumerate(todays_facts):
            if fact["end_time"]:
                fact_time = "%s - %s " % (fact["start_time"].strftime("%H:%M"),
                                       fact["end_time"].strftime("%H:%M"))
            else:
                fact_time = fact["start_time"].strftime("%H:%M ")

            duration = 24 * 60 * fact["delta"].days + fact["delta"].seconds / 60

            add_cell(fact_time, 0, rownum)

            name_tags = gtk.HBox()
            name_label = gtk.Label(fact['name'])
            name_label.set_alignment(0, 0)
            name_tags.pack_start(name_label)

            tags = widgets.TagBox()
            tags.set_size_request(-1, 27)
            tags.draw(fact["tags"])
            tags.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(65536.0,65536.0,65536.0))

            name_tags.pack_start(tags)
            
            name_tags.pack_start(tags)

            add_cell(name_tags, 1, rownum, (gtk.EXPAND | gtk.FILL), ())
            
            

            add_cell(stuff.format_duration(duration), 2, rownum, gtk.FILL, ())

            resume_button = gtk.LinkButton("resume:%d" % fact['id'])
            resume_button.set_label(_("Resume"))
            add_cell(resume_button, 3, rownum, (), ())

            resume_button = gtk.LinkButton("edit:%d" % fact['id'])
            resume_button.set_label(_("Edit"))
            add_cell(resume_button, 4, rownum, (), ())



    def on_activity_text_changed(self, widget):
        self.get_widget("switch_activity").set_sensitive(widget.get_text() != "")

    def on_switch_activity_clicked(self, widget):
        runtime.storage.add_fact(self.new_name.get_text().decode('utf8', 'replace'),
                                 self.new_tags.get_text().decode('utf8', 'replace'))
        self.new_name.set_text("")
        self.new_tags.set_text("")

    def on_stop_tracking_clicked(self, widget):
        runtime.storage.touch_fact(runtime.storage.get_last_activity())

    def after_activity_update(self, widget, stuff):
        logging.debug("activity updated")
        self.set_last_activity()
        self.load_today()

    def after_fact_update(self, widget, stuff):
        logging.debug("fact updated")
        self.set_last_activity()
        self.load_today()

    def show(self):
        self.window.show_all()
        
    def get_widget(self, name):
        return self._gui.get_object(name)

if __name__ == "__main__":
    gtk.gdk.threads_init()

    gtk.window_set_default_icon_name("hamster-applet")
    MainWindow().show()
    
    gtk.main()    

