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
import gobject
from lib import stuff, trophies



def from_dbus_fact(fact):
    """unpack the struct into a proper dict"""
    return stuff.Fact(fact[4],
                      start_time  = dt.datetime.utcfromtimestamp(fact[1]),
                      end_time = dt.datetime.utcfromtimestamp(fact[2]) if fact[2] else None,
                      description = fact[3],
                      activity_id = fact[5],
                      category = fact[6],
                      tags = fact[7],
                      date = dt.datetime.utcfromtimestamp(fact[8]).date(),
                      delta = dt.timedelta(days = fact[9] // (24 * 60 * 60),
                                           seconds = fact[9] % (24 * 60 * 60)),
            id = fact[0]
            )

class Storage(gobject.GObject):
    """Hamster client class, communicating to hamster storage daemon via d-bus.
       Subscribe to the `tags-changed`, `facts-changed` and `activities-changed`
       signals to be notified when an appropriate factoid of interest has been
       changed.

       In storage a distinguishment is made between the classificator of
       activities and the event in tracking log.
       When talking about the event we use term 'fact'. For the classificator
       we use term 'activity'.
       The relationship is - one activity can be used in several facts.
       The rest is hopefully obvious. But if not, please file bug reports!
    """
    __gsignals__ = {
        "tags-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "facts-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "activities-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "toggle-called": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        self._connection = None # will be initiated on demand

        self.bus.add_signal_receiver(self._on_tags_changed, 'TagsChanged', 'org.gnome.Hamster')
        self.bus.add_signal_receiver(self._on_facts_changed, 'FactsChanged', 'org.gnome.Hamster')
        self.bus.add_signal_receiver(self._on_activities_changed, 'ActivitiesChanged', 'org.gnome.Hamster')
        self.bus.add_signal_receiver(self._on_toggle_called, 'ToggleCalled', 'org.gnome.Hamster')

        self.bus.add_signal_receiver(self._on_dbus_connection_change, 'NameOwnerChanged',
                                     'org.freedesktop.DBus', arg0='org.gnome.Hamster')
    @staticmethod
    def _to_dict(columns, result_list):
        return [dict(zip(columns, row)) for row in result_list]

    @property
    def conn(self):
        if not self._connection:
            self._connection = dbus.Interface(self.bus.get_object('org.gnome.Hamster',
                                                              '/org/gnome/Hamster'),
                                              dbus_interface='org.gnome.Hamster')
        return self._connection

    def _on_dbus_connection_change(self, name, old, new):
        self._connection = None

    def _on_tags_changed(self):
        self.emit("tags-changed")

    def _on_facts_changed(self):
        self.emit("facts-changed")

    def _on_activities_changed(self):
        self.emit("activities-changed")

    def _on_toggle_called(self):
        self.emit("toggle-called")

    def toggle(self):
        """toggle visibility of the main application window if any"""
        self.conn.Toggle()

    def get_todays_facts(self):
        """returns facts of the current date, respecting hamster midnight
           hamster midnight is stored in gconf, and presented in minutes
        """
        return [from_dbus_fact(fact) for fact in self.conn.GetTodaysFacts()]

    def get_facts(self, date, end_date = None, search_terms = ""):
        """Returns facts for the time span matching the optional filter criteria.
           In search terms comma (",") translates to boolean OR and space (" ")
           to boolean AND.
           Filter is applied to tags, categories, activity names and description
        """
        date = timegm(date.timetuple())
        end_date = end_date or 0
        if end_date:
            end_date = timegm(end_date.timetuple())

        return [from_dbus_fact(fact) for fact in self.conn.GetFacts(date,
                                                                    end_date,
                                                                    search_terms)]

    def get_activities(self, search = ""):
        """returns list of activities name matching search criteria.
           results are sorted by most recent usage.
           search is case insensitive
        """
        return self._to_dict(('name', 'category'), self.conn.GetActivities(search))

    def get_categories(self):
        """returns list of categories"""
        return self._to_dict(('id', 'name'), self.conn.GetCategories())

    def get_tags(self, only_autocomplete = False):
        """returns list of all tags. by default only those that have been set for autocomplete"""
        return self._to_dict(('id', 'name', 'autocomplete'), self.conn.GetTags(only_autocomplete))


    def get_tag_ids(self, tags):
        """find tag IDs by name. tags should be a list of labels
           if a requested tag had been removed from the autocomplete list, it
           will be ressurrected. if tag with such label does not exist, it will
           be created.
           on database changes the `tags-changed` signal is emitted.
        """
        return self._to_dict(('id', 'name', 'autocomplete'), self.conn.GetTagIds(tags))

    def update_autocomplete_tags(self, tags):
        """update list of tags that should autocomplete. this list replaces
           anything that is currently set"""
        self.conn.SetTagsAutocomplete(tags)

    def get_fact(self, id):
        """returns fact by it's ID"""
        return from_dbus_fact(self.conn.GetFact(id))

    def add_fact(self, fact, temporary_activity = False):
        """Add fact. activity name can use the
        `[-]start_time[-end_time] activity@category, description #tag1 #tag2`
        syntax, or params can be stated explicitly.
        Params will take precedence over the derived values.
        start_time defaults to current moment.
        """
        if not fact.activity:
            return None

        serialized = fact.serialized_name()

        start_timestamp = timegm((fact.start_time or dt.datetime.now()).timetuple())

        end_timestamp = fact.end_time or 0
        if end_timestamp:
            end_timestamp = timegm(end_timestamp.timetuple())

        new_id = self.conn.AddFact(serialized,
                                   start_timestamp,
                                   end_timestamp,
                                   temporary_activity)

        # TODO - the parsing should happen just once and preferably here
        # we should feed (serialized_activity, start_time, end_time) into AddFact and others
        if new_id:
            trophies.checker.check_fact_based(fact)
        return new_id

    def stop_tracking(self, end_time = None):
        """Stop tracking current activity. end_time can be passed in if the
        activity should have other end time than the current moment"""
        end_time = timegm((end_time or dt.datetime.now()).timetuple())
        return self.conn.StopTracking(end_time)

    def remove_fact(self, fact_id):
        "delete fact from database"
        self.conn.RemoveFact(fact_id)

    def update_fact(self, fact_id, fact, temporary_activity = False):
        """Update fact values. See add_fact for rules.
        Update is performed via remove/insert, so the
        fact_id after update should not be used anymore. Instead use the ID
        from the fact dict that is returned by this function"""


        start_time = timegm((fact.start_time or dt.datetime.now()).timetuple())

        end_time = fact.end_time or 0
        if end_time:
            end_time = timegm(end_time.timetuple())

        new_id =  self.conn.UpdateFact(fact_id,
                                       fact.serialized_name(),
                                       start_time,
                                       end_time,
                                       temporary_activity)

        trophies.checker.check_update_based(fact_id, new_id, fact)
        return new_id


    def get_category_activities(self, category_id = None):
        """Return activities for category. If category is not specified, will
        return activities that have no category"""
        category_id = category_id or -1
        return self._to_dict(('id', 'name', 'category_id', 'category'), self.conn.GetCategoryActivities(category_id))

    def get_category_id(self, category_name):
        """returns category id by name"""
        return self.conn.GetCategoryId(category_name)

    def get_activity_by_name(self, activity, category_id = None, resurrect = True):
        """returns activity dict by name and optionally filtering by category.
           if activity is found but is marked as deleted, it will be resurrected
           unless told otherwise in the resurrect param
        """
        category_id = category_id or 0
        return self.conn.GetActivityByName(activity, category_id, resurrect)

    # category and activity manipulations (normally just via preferences)
    def remove_activity(self, id):
        self.conn.RemoveActivity(id)

    def remove_category(self, id):
        self.conn.RemoveCategory(id)

    def change_category(self, id, category_id):
        return self.conn.ChangeCategory(id, category_id)

    def update_activity(self, id, name, category_id):
        return self.conn.UpdateActivity(id, name, category_id)

    def add_activity(self, name, category_id = -1):
        return self.conn.AddActivity(name, category_id)

    def update_category(self, id, name):
        return self.conn.UpdateCategory(id, name)

    def add_category(self, name):
        return self.conn.AddCategory(name)
