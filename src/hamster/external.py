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
from lib import rt

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
        elif self.source == "rt":
            self.rt_url = conf.get("rt_url")
            self.rt_user = conf.get("rt_user")
            self.rt_pass = conf.get("rt_pass")
            self.rt_query = conf.get("rt_query")
            self.rt_category = conf.get("rt_category_field")
            if self.rt_url and self.rt_user and self.rt_pass:
                try:
                    self.tracker = rt.Rt(self.rt_url, self.rt_user, self.rt_pass)
                    if not self.tracker.login():
                        self.source = ""
                except:
                    self.source = ""
            else:
                self.source = ""
        
    def get_activities(self, query = None):
        if not self.source:
            return []

        if self.source == "evo":
            return [activity for activity in get_eds_tasks()
                         if query is None or activity['name'].startswith(query)]
        elif self.source == "rt":
            activities = self.__extract_from_rt(query, self.rt_query)
            direct_ticket = None
            if query and re.match("^[0-9]+$", query):
                ticket = self.tracker.get_ticket(query)
                if ticket:
                    direct_ticket = self.__extract_activity_from_ticket(ticket)
            if direct_ticket:
                activities.append(direct_ticket)
            if len(activities) <= 2 and not direct_ticket and len(query) > 4:
                li = query.split(' ')
                rt_query = " AND ".join(["Subject LIKE '%s'" % (q) for q in li]) + " AND (Status='new' OR Status='open')"
                #logging.warn(rt_query)
                third_activities = self.__extract_from_rt(query, rt_query)
                if activities and third_activities:
                    activities.append({"name": "---------------------", "category": "other open"})
                activities.extend(third_activities)
            return activities
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
        
    def get_ticket_category(self, ticket_id):
        ticket = self.tracker.get_ticket(ticket_id)
        return self.__extract_cat_from_ticket(ticket)
    
    def __extract_activity_from_ticket(self, ticket):
        #activity = {}
        ticket_id = ticket['id']
        #logging.warn(ticket)
        if 'ticket/' in ticket_id:
            ticket_id = ticket_id[7:]
        ticket['name'] = '#'+ticket_id+': '+ticket['Subject']
        if 'Owner' in ticket and ticket['Owner']!=self.rt_user:
            ticket['name'] += " (%s)" % ticket['Owner'] 
        ticket['category'] = self.__extract_cat_from_ticket(ticket)
        ticket['rt_id']=ticket_id;
        return ticket
    
    def __extract_from_rt(self, query = None, rt_query = None):
        activities = []
        results = self.tracker.search_simple(rt_query)
        for ticket in results:
            activity = self.__extract_activity_from_ticket(ticket)
            if query is None or all(item in activity['name'].lower() for item in query.lower().split(' ')):
                activities.append(activity)
        return activities
        
    def __extract_cat_from_ticket(self, ticket):
        category = "RT"
        if 'Queue' in ticket:
            category = ticket['Queue']
        if self.rt_category in ticket:
            category = ticket[self.rt_category]
#        owner = None
#        if 'Owner' in ticket:
#            owner = ticket['Owner']
#        if owner and owner!=self.rt_user:
#            category += ":"+owner
        return category

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
