# - coding: utf-8 -

# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>
# Copyright (C) 2007-2009 Toms Baugis <toms.baugis@gmail.com>

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


import datetime as dt
from calendar import timegm
import dbus, dbus.mainloop.glib

def debus(value):
    """recasts dbus types to the basic ones. should be quite an overhead"""

    if isinstance(value, dbus.Array):
        return [debus(val) for val in value]

    elif isinstance(value, dbus.Dictionary):
        return dict([(debus(key), debus(val)) for key, val in value.items()])

    elif isinstance(value, unicode):
        return unicode(value)
    elif isinstance(value, int):
        return int(value)
    elif isinstance(value, bool):
        return bool(value)

    return value

def from_dbus_fact(fact):
    """unpack the struct into a proper dict"""
    return dict(id = fact[0],
                start_time  = dt.datetime.utcfromtimestamp(fact[1]),
                end_time = dt.datetime.utcfromtimestamp(fact[2]) if fact[2] else None,
                description = fact[3],
                name = fact[4],
                activity_id = fact[5],
                category = fact[6],
                tags = fact[7],
                date = dt.datetime.utcfromtimestamp(fact[8]).date(),
                delta = dt.timedelta(days = fact[9] // (24 * 60 * 60),
                                     seconds = fact[9] % (24 * 60 * 60))
               )


class Storage(object):
    def __init__(self, parent = None):
        self.parent = parent

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        hamster_conn = dbus.Interface(bus.get_object('org.gnome.Hamster',
                                                     '/org/gnome/Hamster'),
                                      dbus_interface='org.gnome.Hamster')
        self.conn = hamster_conn

        if parent:
            bus.add_signal_receiver(self.on_tags_changed, 'TagsChanged', 'org.gnome.Hamster')
            bus.add_signal_receiver(self.on_facts_changed, 'FactsChanged', 'org.gnome.Hamster')
            bus.add_signal_receiver(self.on_activities_changed, 'ActivitiesChanged', 'org.gnome.Hamster')


    def on_tags_changed(self):
        self.parent.dispatch('new_tags_added')

    def on_facts_changed(self):
        self.parent.dispatch('day_updated')

    def on_activities_changed(self):
        self.parent.dispatch('activity_updated')


    def get_todays_facts(self):
        return [from_dbus_fact(fact) for fact in self.conn.GetTodaysFacts()]

    def get_facts(self, date, end_date = 0, search_terms = ""):
        date = timegm(date.timetuple())
        if end_date:
            end_date = timegm(end_date.timetuple())

        return [from_dbus_fact(fact) for fact in self.conn.GetFacts(date,
                                                                    end_date,
                                                                    search_terms)]


    def get_autocomplete_activities(self, search = ""):
        return self.conn.GetAutocompleteActivities(search)

    def get_category_list(self):
        return self.conn.GetCategories()

    def get_tags(self, autocomplete = None):
        return self.conn.GetTags(True)


    def get_tag_ids(self, tags):
        return self.conn.GetTagIds(tags)

    def update_autocomplete_tags(self, tags):
        self.conn.SetTagsAutocomplete(tags)

    def get_fact(self, id):
        return from_dbus_fact(self.conn.GetFact(id))

    def add_fact(self, activity_name, tags = '', start_time = None, end_time = 0,
                                      category_name = None, description = None):

        if start_time:
            start_time = timegm(start_time.timetuple())
        else:
            start_time = 0

        if end_time:
            end_time = timegm(end_time.timetuple())
        else:
            end_time = 0

        category_name = category_name or ''
        description = description or ''

        return self.conn.AddFact(activity_name, tags, start_time, end_time, category_name, description)

    def stop_tracking(self, end_time = None):
        end_time = timegm((end_time or dt.datetime.now()).timetuple())
        return self.conn.StopTracking(end_time)

    def remove_fact(self, fact_id):
        self.conn.RemoveFact(fact_id)

    def update_fact(self, fact_id, activity_name, tags, start_time = 0, end_time = 0, category_name = '', description = ''):
        category_name = category_name or '' # so to override None
        description = description or '' # so to override None

        if start_time:
            start_time = timegm(start_time.timetuple())
        if end_time:
            end_time = timegm(end_time.timetuple())
        else:
            end_time = 0

        return self.conn.UpdateFact(fact_id, activity_name, tags, start_time, end_time, category_name, description)


    def get_activities(self, category_id = None):
        category_id = category_id or -1
        return self.conn.GetActivities(category_id)


    def get_last_activity(self):
        return self.conn.GetLastActivity()

    def remove_activity(self, id):
        self.conn.RemoveActivity(id)

    def remove_category(self, id):
        self.conn.RemoveCategory(id)

    def move_activity(self, source_id, target_order, insert_after = True):
        self.conn.MoveActivity(source_id, target_order, insert_after)

    def change_category(self, id, category_id):
        return self.conn.ChangeCategory(id, category_id)

    def swap_activities(self, id1, priority1, id2, priority2):
        self.conn.SwapActivities(id1, priority1, id2, priority2)

    def update_activity(self, id, name, category_id):
        return self.conn.UpdateActivity(id, name, category_id)

    def add_activity(self, name, category_id = -1):
        return self.conn.AddActivity(name, category_id)

    def update_category(self, id, name):
        return self.conn.UpdateCategory(id, name)

    def add_category(self, name):
        return self.conn.AddCategory(name)


    def get_category_by_name(self, category):
        return self.conn.GetCategoryByName(category)

    def get_activity_by_name(self, activity, category_id = None, ressurect = True):
        category_id = category_id or 0
        return self.conn.GetActivityByName(activity, category_id, ressurect)
