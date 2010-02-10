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

import logging
import dbus
import dbus.service
import datetime
from calendar import timegm

from configuration import runtime

# DBus service parameters
HAMSTER_URI = "org.gnome.Hamster"


class HamsterDbusController(dbus.service.Object):
    # Non-initialized current fact id
    current_fact_id = 0

    def __init__(self, bus_name):
        """HamsterDbusController encapsulates the dbus api logic
        for the hamster-applet and performs the necesary conversion
        between dbus types and hamster-applet data types
        """
        try:
            dbus.service.Object.__init__(self, bus_name, "/org/gnome/Hamster")
        except KeyError:
            # KeyError is thrown when the dbus interface is taken
            # that is there is other hamster running somewhere
            logging.warn("D-Bus interface registration failed - other hamster running somewhere")

    @staticmethod
    def _to_dbus_fact(fact):
        """Perform the conversion between fact database query and
        dbus supported data types
        """
        if not fact:
            return dbus.Dictionary({}, signature='sv')

        fact = dict(fact)
        for key in fact.keys():
            fact[key] = fact[key] or 0

            # make sure we return correct type where strings are expected
            if not fact[key] and key in ('name', 'category', 'description'):
                fact[key] = ''

            # convert times to gmtime
            if isinstance(fact[key], datetime.datetime) or isinstance(fact[key], datetime.date):
                fact[key] = timegm(fact[key].timetuple())
            elif isinstance(fact[key], datetime.timedelta) :
                fact[key] = fact[key].days * 24 * 60 * 60 + fact[key].seconds

        return fact


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
        u end_time: Seconds since epoch (timestamp)
        as tags: List of tags used
        """
        return HamsterDbusController._to_dbus_fact(runtime.storage.get_last_activity())

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
        as tags: List of tags used
        """
        return HamsterDbusController._to_dbus_fact(runtime.storage.get_fact(fact_id))

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
        as tags: List of tags used
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
            facts.append(HamsterDbusController._to_dbus_fact(fact))

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
            activities.append((act['name'] or '', act['category'] or ''))
        return activities

    @dbus.service.method(HAMSTER_URI, out_signature='as')
    def GetTags(self):
        """Returns array of all active tags"""
        tags = dbus.Array([], signature='s')

        for tag in runtime.storage.get_tags():
            tags.append(tag['name'] or '')
        return tags

    @dbus.service.method(HAMSTER_URI, in_signature='s')
    def SetAutocompleteTags(self, tags):
        """Update autocomplete tags with the given comma-delimited list.
        If a tag is gone missing, it will be deleted if it has not been used.
        If it has been used, it will be marked as not to be used in autocomplete
        (and revived on first use). New tags will just appear.
        Parameters:
        s tags: Comma-separated tags ("tag1, tag2, tag3, and so, on")
        """
        runtime.storage.update_autocomplete_tags(tags)

    @dbus.service.method(HAMSTER_URI, out_signature='ss')
    def GetCurrentActivity(self):
        """Returns the Activity currently being used, or blanks if Hamster is not tracking currently
        s activity: Activity name
        s category: Category name
        """
        last_activity = runtime.storage.get_last_activity()
        if last_activity:
            return (last_activity['name'] or '', last_activity['category'] or '')
        else:
            return ('', '')

    @dbus.service.method(HAMSTER_URI, out_signature='as')
    def GetCategories(self):
        """Gets all defined categories
        Returns Array of:
        s category: Category name
        """
        categories = dbus.Array([], signature='s')
        for cat in runtime.storage.get_category_list():
            categories.append(cat['name'] or '')
        return categories

    @dbus.service.method(HAMSTER_URI, in_signature='suu', out_signature='i')
    def AddFact(self, activity, start_time, end_time):
        """Add a new fact
        Parameters:
        s activity: Activity name with optional category, description and tags
          in the form 'activity_name[@category_name][,description [#tag1 #tagN]]'
          Activity, matching category and tags will be refered or created on the
          fly.
          Note that tags go into description - this is in order to reduce number
          of action symbols in activity string
        u start_time: Seconds since epoch (timestamp). Use 0 for 'now'
        u end_time: Seconds since epoch (timestamp). Use 0 for ongoing task
        """
        #TODO: Assert start > end ?
        start, end = None, None

        if start_time:
            start = datetime.datetime.utcfromtimestamp(start_time)
        if end_time:
            end = datetime.datetime.utcfromtimestamp(end_time)

        return runtime.storage.add_fact(activity, "", start, end)

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
    def RemoveActivity(self, activity_name, category):
        """Removes an activity
        Parameters:
        s activity: Activity name
        s category: Category name. Use '' for Unsorted activity
        """
        category_id = runtime.storage.get_category_by_name(category)
        activity = runtime.storage.get_activity_by_name(activity_name, category_id)

        if activity:
            runtime.storage.remove_activity(activity['id'])

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
