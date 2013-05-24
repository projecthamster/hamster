# - coding: utf-8 -

# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>
# Copyright (C) 2008, 2010 Toms Bauģis <toms.baugis at gmail.com>

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
from configuration import conf
import gobject
import re
import dbus, dbus.mainloop.glib
import json
from lib import rt
from lib import redmine

try:
    import evolution
    from evolution import ecal
except:
    evolution = None
    
class ActivitiesSource(gobject.GObject):
    def __init__(self):
        logging.debug('external init')
        gobject.GObject.__init__(self)
        self.source = conf.get("activities_source")
        self.__gtg_connection = None

        if self.source == "evo" and not evolution:
            self.source == "" # on failure pretend that there is no evolution
        elif self.source == "gtg":
            gobject.GObject.__init__(self)
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        elif self.source == "redmine":
            self.rt_url = conf.get("rt_url")
            self.rt_apikey = conf.get("rt_apikey")
            self.rt_category = conf.get("rt_category_field")
            if self.rt_url and self.rt_apikey:
                try:
                    self.tracker = redmine.Redmine(self.rt_url, auth=(self.rt_apikey,"placeholder"))
                    if not self.tracker:
                        self.source = ""

                except:
                    self.source = ""
            else:
                self.source = ""
    
    #PRL not used anymore
    def get_activities(self, query = None):
        if not self.source:
            return []
        #######################################################################################
        #######################################################################################
        if self.source == "redmine":
            activities = self.__extract_from_redmine(query)
            direct_issue = None
            if query and re.match("^[0-9]+$", query):
                issue = self.tracker.getIssue(query)
                if issue:
                    direct_issue = self.__extract_activity_from_issue(issue)
            if direct_issue:
                activities.append(direct_issue)
            if len(activities) <= 2 and not direct_issue and len(query) > 4:
                criteria = ({'status_id': 'open', 'subject': query})
                #logging.warn(criteria)
                third_activities = self.__extract_from_redmine(query, criteria)
                if activities and third_activities:
                    activities.append({"name": "---------------------", "category": "other open"})
                activities.extend(third_activities)
            return activities
        #######################################################################################
        #######################################################################################
        elif self.source == "evo":
            return [activity for activity in get_eds_tasks()
                         if query is None or activity['name'].startswith(query)]
        elif self.source == "gtg":
            conn = self.__get_gtg_connection()
            if not conn:
                return []

            activities = []

            tasks = []
            try:
                tasks = conn.get_tasks()
            except dbus.exceptions.DBusException:  #TODO too lame to figure out how to connect to the disconnect signal
                self.__gtg_connection = None
                return self.get_activities(query) # reconnect


            for task in tasks:
                if query is None or task['title'].lower().startswith(query):
                    name = task['title']
                    if len(task['tags']):
                        name = "%s, %s" % (name, " ".join([tag.replace("@", "#") for tag in task['tags']]))

                    activities.append({"name": name, "category": ""})

            return activities
    
    def __extract_activity_from_issue(self, issue):
        activity = {}
        issue_id = issue.id
        activity['name']    = '#'+str(issue_id)+': '+issue.subject
        activity['rt_id']   = issue_id;
        activity['category']= "";
        activity['mine']    = 0
        return activity
        
    def __extract_from_redmine(self, query = None, criteria = None):
        activities = []
        results = self.tracker.getIssues(criteria)
        for issue in results:
            activity = self.__extract_activity_from_issue(issue)
            if query is None or all(item in activity['name'].lower() for item in query.lower().split(' ')):
                activities.append(activity)
        return activities

    def __get_gtg_connection(self):
        bus = dbus.SessionBus()
        if self.__gtg_connection and bus.name_has_owner("org.GTG"):
            return self.__gtg_connection

        if bus.name_has_owner("org.GTG"):
            self.__gtg_connection = dbus.Interface(bus.get_object('org.GTG', '/org/GTG'),
                                                   dbus_interface='org.GTG')
            return self.__gtg_connection
        else:
            return None


    def get_eds_tasks():
        try:
            sources = ecal.list_task_sources()
            tasks = []
            if not sources:
                # BUG - http://bugzilla.gnome.org/show_bug.cgi?id=546825
                sources = [('default', 'default')]

            for source in sources:
                category = source[0]

                data = ecal.open_calendar_source(source[1], ecal.CAL_SOURCE_TYPE_TODO)
                if data:
                    for task in data.get_all_objects():
                        if task.get_status() in [ecal.ICAL_STATUS_NONE, ecal.ICAL_STATUS_INPROCESS]:
                            tasks.append({'name': task.get_summary(), 'category' : category})
            return tasks
        except Exception, e:
            logging.warn(e)
            return []


    def get_redmine_activities(self, criteria=({})):
        if not self.source:
            return []
        if self.source == "redmine":
            activities = []
            results = self.tracker.getIssues(criteria)
            for issue in results:
                activity = self.__extract_activity_from_issue(issue)
                activities.append(activity)
            return activities

    def get_all_redmine_activities(self):
        if not self.source:
            return []
        activities = []
        if self.source == "redmine":
            keep_going = True
            offset = 0
            while keep_going:
                results = self.tracker.getIssues({'offset':offset})
                print len(results)
                if len(results) < 100: keep_going = False
                else: offset += 100
                for issue in results:
                    activity = self.__extract_activity_from_issue(issue)
                    activities.append(activity)
        return activities
