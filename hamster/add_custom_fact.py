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
import hamster.eds

import time
import datetime

GLADE_FILE = "add_custom_fact.glade"


class CustomFactController:
    def __init__(self,  fact_date = None, fact_id = None):
        self.wTree = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, GLADE_FILE))
        self.window = self.get_widget('custom_fact_window')

        # load window of activity switcher and todays view
        self.items = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)
        self.activities = gtk.ListStore(gobject.TYPE_STRING)
        self.completion = gtk.EntryCompletion()
        self.completion.set_model(self.activities)
        self.completion.set_text_column(0)
        self.completion.set_minimum_key_length(1) 
        activity_list = self.wTree.get_widget('activity-list')
        activity_list.set_model(self.items)
        activity_list.set_text_column(0)
        activity_list.child.set_completion(self.completion)


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
        if fact_id:
            fact = storage.get_fact(fact_id)
            print fact
            self.get_widget('start_date').set_time(int(time.mktime(fact["start_time"].timetuple())))
            self.get_widget('start_time').set_text("%02d:%02d" % (fact["start_time"].hour, fact["start_time"].minute))

            self.get_widget('activity_name').set_text(fact["name"])
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


        self.wTree.signal_autoconnect(self)
        
    def refresh_menu(self):
        all_activities = storage.get_activities()
        self.activities.clear()
        for activity in all_activities:
            self.activities.append([activity['name']])

        activity_list = self.get_widget('activity-list')
        store = activity_list.get_model()
        store.clear()

        #populate fresh list from DB
        activities = storage.get_sorted_activities()
        prev_item = None

        today = datetime.date.today()
        for activity in activities:
            item = store.append([activity['name'], activity['id']])

        tasks = hamster.eds.get_eds_tasks()
        for activity in tasks:
            item = store.append([activity['name'], -1])
            

        return True

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.wTree.get_widget(name)

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
      if (event_key.keyval == gtk.keysyms.Escape):
        self.window.destroy()

