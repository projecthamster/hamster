# - coding: utf-8 -

# Copyright (C) 2008, J. Félix Ontañón <fontanon at emergya dot es>
# Thanks to John Carr for helpful patching

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

import dbus
import dbus.service
import datetime
from calendar import timegm

from configuration import runtime

# DBus service parameters
HAMSTER_URI = "org.gnome.Hamster"
HAMSTER_PATH = "/org/gnome/Hamster"

# Data-keys used in hamster to refer 
# facts, categories and activities
FCT_KEY = 'id'
ACT_KEY = 'name'
CAT_KEY = 'category'
DSC_KEY = 'description'
SRT_KEY = 'start_time'
END_KEY = 'end_time'

class HamsterDbusController(dbus.service.Object):
    # Non-initialized current fact id
    current_fact_id = 0

    def __init__(self, bus_name):
        """HamsterDbusController encapsulates the dbus api logic
        for the hamster-applet and performs the necesary conversion
        between dbus types and hamster-applet data types
        """
        try:
            dbus.service.Object.__init__(self, bus_name, HAMSTER_PATH)
        except KeyError:
            # KeyError is thrown when the dbus interface is taken
            # that is there is other hamster running somewhere
            print "D-Bus interface registration failed - other hamster running somewhere"
            pass

    @staticmethod
    def to_dbus_fact(fact):
        """Perform the conversion between fact database query and 
        dbus supported data types
        """

        if not fact:
            return dbus.Dictionary({}, signature='sv')

        # Default fact values
        dbus_fact = {FCT_KEY: 0, ACT_KEY:'', CAT_KEY:'', DSC_KEY:'',
                SRT_KEY:0, END_KEY:0}

        # Workaround for fill values
        fact_keys = fact.keys()

        for key in (FCT_KEY, ACT_KEY, CAT_KEY, DSC_KEY):
            if key in fact_keys and fact[key]:
                dbus_fact[key] = fact[key]

        for key in (SRT_KEY, END_KEY):
            if key in fact_keys and fact[key]:
                # Convert datetime to unix timestamp (seconds since epoch)
                dbus_fact[key] = timegm(fact[key].timetuple())

        return dbus_fact

    @dbus.service.method(HAMSTER_URI, out_signature='a{sv}')
    def GetCurrentFact(self):
        """Gets the current displaying fact
        Returns Dict of:
        i id: Unique fact identifier
        s name: Activity name
        s category: Category name
        s description: Description of the fact
        u start_time: Seconds since epoch (timestamp)
        u end_time: Seconds since epoch (timestamp)
        """
        return HamsterDbusController.to_dbus_fact(runtime.storage.get_last_activity())

    @dbus.service.method(HAMSTER_URI, in_signature='i', out_signature='a{sv}')
    def GetFactById(self, fact_id):
        """Gets the current displaying fact
        Parameters:
        i id: Unique fact identifier
        Returns Dict of:
        i id: Unique fact identifier
        s name: Activity name
        s category: Category name
        s description: Description of the fact
        u start_time: Seconds since epoch (timestamp)
        u end_time: Seconds since epoch (timestamp)
        """
        return HamsterDbusController.to_dbus_fact(runtime.storage.get_fact(fact_id))

    @dbus.service.method(HAMSTER_URI, in_signature='uu', out_signature='aa{sv}')
    def GetFacts(self, start_date, end_date):
        """Gets facts between the day of start_date and the day of end_date.
        Parameters:
        u start_date: Seconds since epoch (timestamp). Use 0 for today
        u end_date: Seconds since epoch (timestamp). Use 0 for today
        Returns Array of fact where fact it's Dict of:
        i id: Unique fact identifier
        s name: Activity name
        s category: Category name
        s description: Description of the fact
        u start_time: Seconds since epoch (timestamp)
        u end_time: Seconds since epoch (timestamp)
        """
        #TODO: Assert start > end ?
        if start_date:
            start = datetime.datetime.utcfromtimestamp(start_date).date()
        else:
            start = datetime.date.today()

        if end_date:
            end = datetime.datetime.utcfromtimestamp(end_date).date()
        else:
            end = datetime.date.today()

        facts = dbus.Array([], signature='a{sv}')
        for fact in runtime.storage.get_facts(start, end):
            facts.append(HamsterDbusController.to_dbus_fact(fact))

        return facts

    @dbus.service.method(HAMSTER_URI, out_signature='a(ss)')
    def GetActivities(self):
        """Gets all defined activities with matching category
        Returns Array of:
        s activity: Activity name
        s category: Category name
        """
        activities = dbus.Array([], signature='(ss)')
        for act in runtime.storage.get_autocomplete_activities():
            activities.append((act[ACT_KEY] or '', act[CAT_KEY] or ''))
        return activities

    @dbus.service.method(HAMSTER_URI, out_signature='as')
    def GetCategories(self):
        """Gets all defined categories
        Returns Array of:
        s category: Category name
        """
        categories = dbus.Array([], signature='s')
        for cat in runtime.storage.get_category_list():
            categories.append(cat[ACT_KEY] or '')
        return categories

    @dbus.service.method(HAMSTER_URI, in_signature='suu', out_signature='i')
    def AddFact(self, activity, start_time, end_time):
        """Add a new fact
        Parameters:
        s activity: Activity name with optional category and/or description
                    in the form 'activity_name[@category_name][,description]'
                    Activity and matching category will be refered or created 
                    on the fly.
        u start_time: Seconds since epoch (timestamp). Use 0 for 'now'
        u end_time: Seconds since epoch (timestamp). 
                    Use 0 for 'in progress task'
        """
        #TODO: Assert start > end ?
        start, end = None, None

        if start_time:
            start = datetime.datetime.utcfromtimestamp(start_time)
        if end_time:
            end = datetime.datetime.utcfromtimestamp(end_time)

        fact = runtime.storage.add_fact(activity, start, end)
        return fact[FCT_KEY]

    @dbus.service.method(HAMSTER_URI, in_signature='ss')
    def AddActivity(self, activity, category):
        """Add a new activity
        Parameters:
        s activity: Activity name
        s category: Category name. It will be created if it doesn't exists
                    Use '' for Unsorted activity
        """
        category_id = None

        if category:
            category_id = runtime.storage.get_category_by_name(category) \
                    or runtime.storage.add_category(category)

        runtime.storage.add_activity(activity, category_id)

    @dbus.service.method(HAMSTER_URI, in_signature='s')
    def AddCategory(self, category):
        """Add a new category
        Parameters:
        s category: category name
        """
        if category and not runtime.storage.get_category_by_name(category):
            runtime.storage.add_category(category)

    @dbus.service.method(HAMSTER_URI)
    def StopTracking(self):
        """Stops the current fact tracking"""
        last_activity = runtime.storage.get_last_activity()
        if last_activity:
            runtime.storage.touch_fact(last_activity)

    @dbus.service.method(HAMSTER_URI, in_signature='i')
    def RemoveFact(self, fact_id):
        """Removes a fact
        Parameters:
        i id: Unique fact identifier
        """
        runtime.storage.remove_fact(fact_id)

    @dbus.service.method(HAMSTER_URI, in_signature='ss')
    def RemoveActivity(self, activity, category):
        """Removes an activity
        Parameters:
        s activity: Activity name
        s category: Category name. Use '' for Unsorted activity
        """
        category_id = runtime.storage.get_category_by_name(category)
        activity_id = runtime.storage.get_activity_by_name(activity, category_id)

        if activity_id:
            runtime.storage.remove_activity(activity_id)

    @dbus.service.method(HAMSTER_URI, in_signature='s')
    def RemoveCategory(self, category):
        """Removes a category
        Parameters:
        s category: Category name
        """
        category_id = runtime.storage.get_category_by_name(category)
        if category_id:
            runtime.storage.remove_category(category_id)

    @dbus.service.signal(HAMSTER_URI, signature='i')
    def FactUpdated(self, fact_id):
        """Notifies fact changes
        Parameters:
        i id: Unique fact identifier
        """
        self.current_fact_id = fact_id

    @dbus.service.signal(HAMSTER_URI)
    def TrackingStopped(self):
        """Notifies the fact tracking has been stopped"""
        self.current_fact_id = 0
