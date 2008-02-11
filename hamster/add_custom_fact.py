#!/usr/bin/env python
import pygtk
pygtk.require('2.0')

import os
import gtk
import gtk.glade
import gobject
import gnome.ui

from hamster import dispatcher, storage, SHARED_DATA_DIR
import hamster.eds

import time
import datetime

GLADE_FILE = "add_custom_fact.glade"


class CustomFactController:
    def __init__(self,  parent, fact_date = None):
        self.parent = parent
        
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
            self.hours.append([str(i) + ":" + "00" ])
            self.hours.append([str(i) + ":" + "30" ])

        # build the menu
        self.refresh_menu()
        
        self.get_widget('end_time_mode').set_active(0)
        
        self.get_widget('start_time_combo').set_model(self.hours)        
        self.get_widget('start_time').set_text(time.strftime("%H:%M"))
        
        self.get_widget('end_time_combo').set_model(self.hours)        
        #if fact_date:
        #    self.get_widget('activity_time').set_time(time.mktime(fact_date.timetuple()))


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
            self.get_widget("end_date").set_time(self.get_widget('start_date').get_time())
            self.get_widget("end_time").set_text(self.get_widget('start_time').get_text())
            self.get_widget("fact_end_until").show()
        
        elif selected == 2:
            # selected to enter duration
            self.get_widget("fact_end_for").show()

    def _get_secs(self, prefix):
        # adds symbolic time to date in seconds
        a_date = self.get_widget(prefix + '_date').get_time()
        a_time = self.get_widget(prefix + '_time').get_text()
        return a_date + int(a_time[:2]) * 3600 + int(a_time[3:5]) * 60
        
    
    def on_ok_clicked(self, button):
        activity = self.get_widget("activity-list").get_child().get_text()
        start_time = datetime.datetime.fromtimestamp(self._get_secs("start"))

        new_fact = storage.add_fact(activity, start_time)
        

        end_time_mode = self.get_widget("end_time_mode").get_active()
        
        if end_time_mode == 0:  # TODO - check if our fact is the last one
            self.parent.last_activity = new_fact
            dispatcher.dispatch("day_updated", new_fact['start_time'])  # let them know that we have new entry
            
        else: #we have end time, so let's update it
            if end_time_mode == 1: # specified end  time
                print "setting specified end time"
                end_time = datetime.datetime.fromtimestamp(self._get_secs("end"))
                
            else: #duration
                print "setting duration"
                # duration in seconds
                duration = self.get_widget("duration_hours").get_value() * 3600
                duration = duration + self.get_widget("duration_mins").get_value() * 60
                end_time_secs = self._get_secs("start") + duration

                end_time = datetime.datetime.fromtimestamp(end_time_secs)
                
            print end_time

            storage.touch_fact(new_fact, end_time)
        
        
        self.window.destroy()
        
    def on_cancel_clicked(self, button):
        self.window.destroy()
        
    def on_combo_changed(self, combo):
      # do not allow empty tasks
      activity = self.get_widget("activity-list").get_child().get_text()
      self.get_widget("ok").set_sensitive(activity != '')

    
if __name__ == '__main__':
    controller = OverviewController()
    controller.show()
    gtk.main()


