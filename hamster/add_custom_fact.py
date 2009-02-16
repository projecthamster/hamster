# -*- coding: utf-8 -*-

# Copyright (C) 2007, 2008 Toms Bauģis <toms.baugis at gmail.com>

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
import gtk
import gobject

from hamster import dispatcher, storage, SHARED_DATA_DIR
from hamster.stuff import *

import hamster.eds

import time
import datetime

GLADE_FILE = "add_custom_fact.glade"


class CustomFactController:
    def __init__(self,  fact_date = None, fact_id = None):
        self.glade = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, GLADE_FILE))
        self.window = self.get_widget('custom_fact_window')

        self.set_dropdown()

        self.hours = gtk.ListStore(gobject.TYPE_STRING)
        
        for i in range(24):
            self.hours.append(["%02d:00" % i ])
            self.hours.append(["%02d:30" % i ])

        # build the menu
        self.refresh_menu()
        
        self.get_widget('end_time_mode').set_active(0)
        
        self.get_widget('start_time_combo').set_model(self.hours)        
        self.get_widget('start_time').set_text(time.strftime("%H:%M"))
        
        self.get_widget('end_time_combo').set_model(self.hours)        
        if fact_date:
            self.get_widget('start_date').set_time(int(time.mktime(fact_date.timetuple())))
        
        # handle the case when we get fact_id - that means edit!
        self.fact_id = fact_id
        self.get_widget("ok").set_sensitive(False)

        if fact_id:
            fact = storage.get_fact(fact_id)
            print fact
            self.get_widget('start_date').set_time(int(time.mktime(fact["start_time"].timetuple())))
            self.get_widget('start_time').set_text("%02d:%02d" % (fact["start_time"].hour, fact["start_time"].minute))

            self.get_widget('activity_name').set_text(fact["name"])
            
            buf = gtk.TextBuffer()
            buf.set_text(fact["description"] or "")
            self.get_widget('description').set_buffer(buf)

            self.get_widget("ok").set_sensitive(True)
            self.get_widget("ok").set_label("gtk-save")
            self.window.set_title(_("Update activity"))
            
            if fact["end_time"]:
                self.get_widget("end_time_mode").set_active(1)
                self.get_widget("fact_end_until").show()
                self.get_widget('end_time').set_text("%02d:%02d" % (fact["end_time"].hour, fact["end_time"].minute))
                
                # fill also delta for those relative types, heh
                for_delta = fact["end_time"] - fact["start_time"]
                for_hours = for_delta.seconds / 3600
                for_minutes = (for_delta.seconds - (for_hours * 3600)) / 60
                self.get_widget('duration_hours').set_value(for_hours)
                self.get_widget('duration_mins').set_value(for_minutes)


        self.glade.signal_autoconnect(self)

    def set_dropdown(self):
        # set up drop down menu
        self.activity_list = self.glade.get_widget('activity-list')
        self.activity_list.set_model(gtk.ListStore(gobject.TYPE_STRING,
                                                   gobject.TYPE_STRING,
                                                   gobject.TYPE_STRING))

        self.activity_list.clear()
        activity_cell = gtk.CellRendererText()
        self.activity_list.pack_start(activity_cell, True)
        self.activity_list.add_attribute(activity_cell, 'text', 0)
        category_cell = CategoryCell()  
        self.activity_list.pack_start(category_cell, False)
        self.activity_list.add_attribute(category_cell, 'text', 1)
        
        self.activity_list.set_property("text-column", 2)


        # set up autocompletition
        self.activities = gtk.ListStore(gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING)
        completion = gtk.EntryCompletion()
        completion.set_model(self.activities)

        activity_cell = gtk.CellRendererText()
        completion.pack_start(activity_cell, True)
        completion.add_attribute(activity_cell, 'text', 0)
        completion.set_property("text-column", 2)

        category_cell = CategoryCell()  
        completion.pack_start(category_cell, False)
        completion.add_attribute(category_cell, 'text', 1)

        def match_func(completion, key, iter):
            model = completion.get_model()
            text = model.get_value(iter, 2)
            if text and text.startswith(key):
                return True
            return False

        completion.set_match_func(match_func)
        completion.set_minimum_key_length(1)
        completion.set_inline_completion(True)

        self.activity_list.child.set_completion(completion)


    def refresh_menu(self):
        #first populate the autocomplete - contains all entries in lowercase
        self.activities.clear()
        all_activities = storage.get_autocomplete_activities()
        for activity in all_activities:
            activity_category = "%s@%s" % (activity['name'], activity['category'])
            self.activities.append([activity['name'],
                                    activity['category'],
                                    activity_category])


        #now populate the menu - contains only categorized entries
        store = self.activity_list.get_model()
        store.clear()

        #populate fresh list from DB
        categorized_activities = storage.get_sorted_activities()

        for activity in categorized_activities:
            activity_category = "%s@%s" % (activity['name'], activity['category'])
            item = store.append([activity['name'],
                                 activity['category'],
                                 activity_category])

        # finally add TODO tasks from evolution to both lists
        tasks = hamster.eds.get_eds_tasks()
        for activity in tasks:
            activity_category = "%s@%s" % (activity['name'], activity['category'])
            self.activities.append([activity['name'],activity['category'],activity_category])
            store.append([activity['name'], activity['category'], activity_category])

        return True

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.glade.get_widget(name)

    def show(self):
        self.window.show()
        
    def on_end_time_mode_changed(self, widget):
        selected = widget.get_active()

        #those will get handy, when user changes end time condition
        self.get_widget("fact_end_until").hide()
        self.get_widget("fact_end_for").hide()

        if selected == 1:
            # selected to enter end date and time
            start_date = datetime.datetime.fromtimestamp(self.get_widget('start_date').get_time())
            if start_date.date() == datetime.date.today():  #in case of today let's add the end time as right now
                end_time = time.strftime("%H:%M")
            else: #otherwise settle to the one we have in start time
                end_time = self.get_widget('start_time').get_text()

            # and set end_time only if it has not been specified before
            if self.get_widget('end_time').get_text() == '':
                self.get_widget('end_time').set_text(end_time)

            self.get_widget("fact_end_until").show()
        
        elif selected == 2:
            # selected to enter duration
            self.get_widget("fact_end_for").show()

    def _get_datetime(self, prefix):
        # adds symbolic time to date in seconds
        a_date = datetime.datetime.fromtimestamp(self.get_widget('start_date').get_time())
        hours, secs = self.get_widget(prefix + '_time').get_text().split(":")        
        return datetime.datetime.combine(a_date, datetime.time(int(hours), int(secs)))
        
    
    def on_ok_clicked(self, button):
        activity = self.get_widget("activity-list").get_child().get_text()
        
        if not activity:
            return False

        # juggle with description - break into parts and then put together
        buf = self.get_widget('description').get_buffer()
        description = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), 0)
        description = description.strip()
        
        # user might also type description in the activity name - strip it here
        # and remember value
        inline_description = None
        if activity.find(",") != -1:
            activity, inline_description  = activity.split(",", 1)
            inline_description = inline_description.strip()
        
        # description field is prior to inline description
        description = description or inline_description
        
        if description:
            activity = "%s, %s" % (activity, description)

        
        
        start_time = self._get_datetime("start")

        end_time = None
        end_time_mode = self.get_widget("end_time_mode").get_active()
        
        if end_time_mode != 0: #we have end time, so let's update it
            if end_time_mode == 1: # specified end  time
                print "setting specified end time"
                end_time = self._get_datetime("end")
                
            else: #duration
                print "setting duration"
                # duration in seconds
                duration = self.get_widget("duration_hours").get_value() * 60
                duration = duration + self.get_widget("duration_mins").get_value()
                end_time_secs = start_time + datetime.timedelta(minutes = duration)

                end_time = end_time_secs
                
            print end_time

        # do some  trickery here - if we were told to update, let's just
        # do insert/delete
        if self.fact_id:
            storage.remove_fact(self.fact_id)

        storage.add_fact(activity, start_time, end_time)

        if not self.fact_id: #hide panel only on add - on update user will want to see confirmation of changes
            dispatcher.dispatch('panel_visible', False)
        
        self.window.destroy()
        
    def on_cancel_clicked(self, button):
        self.window.destroy()
        
    def on_combo_changed(self, combo):
        # do not allow empty tasks
        activity = self.get_widget("activity-list").get_child().get_text()
        self.get_widget("ok").set_sensitive(activity != '')

    def on_window_key_pressed(self, tree, event_key):
        if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w 
              and event_key.state & gtk.gdk.CONTROL_MASK)):
            self.window.destroy()
        elif (event_key.keyval == gtk.keysyms.Return or
              event_key.keyval == gtk.keysyms.KP_Enter):
            self.on_ok_clicked(None)


