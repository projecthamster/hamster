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
    }

    def __init__(self, parent = None):
        gobject.GObject.__init__(self)

        self.parent = parent

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        hamster_conn = dbus.Interface(bus.get_object('org.gnome.Hamster',
                                                     '/org/gnome/Hamster'),
                                      dbus_interface='org.gnome.Hamster')
        self.conn = hamster_conn

        if parent:
            bus.add_signal_receiver(self._on_tags_changed, 'TagsChanged', 'org.gnome.Hamster')
            bus.add_signal_receiver(self._on_facts_changed, 'FactsChanged', 'org.gnome.Hamster')
            bus.add_signal_receiver(self._on_activities_changed, 'ActivitiesChanged', 'org.gnome.Hamster')


    def _on_tags_changed(self):
        self.emit("tags-changed")

    def _on_facts_changed(self):
        self.emit("facts-changed")

    def _on_activities_changed(self):
        self.emit("activities-changed")


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

    def get_autocomplete_activities(self, search = ""):
        """returns list of activities name matching search criteria.
           results are sorted by most recent usage.
           search is case insensitive
        """
        return self.conn.GetAutocompleteActivities(search)

    def get_categories(self):
        """returns list of categories"""
        return self.conn.GetCategories()

    def get_tags(self):
        """returns list of all tags. by default only those that have been set for autocomplete"""
        return self.conn.GetTags()


    def get_tag_ids(self, tags):
        """find tag IDs by name. tags should be a list of labels
           if a requested tag had been removed from the autocomplete list, it
           will be ressurrected. if tag with such label does not exist, it will
           be created.
           on database changes the `tags-changed` signal is emitted.
        """
        return self.conn.GetTagIds(tags)

    def update_autocomplete_tags(self, tags):
        """update list of tags that should autocomplete. this list replaces
           anything that is currently set"""
        self.conn.SetTagsAutocomplete(tags)

    def get_fact(self, id):
        """returns fact by it's ID"""
        return from_dbus_fact(self.conn.GetFact(id))

    def add_fact(self, activity_name, tags = '', start_time = None, end_time = None,
                                      category_name = None, description = None):
        """Add fact. activity name can use `[-]start_time[-end_time] activity@category, description #tag1 #tag2`
        syntax, or params can be stated explicitly.
        Params, except for the start and end times will take precedence over
        derived values.
        start_time defaults to current moment.
        """


        start_time = start_time or 0
        if start_time:
            start_time = timegm(start_time.timetuple())

        end_time = end_time or 0
        if end_time:
            end_time = timegm(end_time.timetuple())

        if isinstance(tags, list): #make sure we send what storage expects
            tags = ", ".join(tags)
        tags = tags or ''

        category_name = category_name or ''
        description = description or ''

        return self.conn.AddFact(activity_name, tags, start_time, end_time, category_name, description)

    def stop_tracking(self, end_time = None):
        """Stop tracking current activity. end_time can be passed in if the
        activity should have other end time than the current moment"""
        end_time = timegm((end_time or dt.datetime.now()).timetuple())
        return self.conn.StopTracking(end_time)

    def remove_fact(self, fact_id):
        "delete fact from database"
        self.conn.RemoveFact(fact_id)

    def update_fact(self, fact_id, activity_name, tags = None, start_time = None, end_time = None, category_name = None, description = None):
        """Update fact values. See add_fact for rules.
        Update is performed via remove/insert, so the
        fact_id after update should not be used anymore. Instead use the ID
        from the fact dict that is returned by this function"""

        category_name = category_name or '' # so to override None
        description = description or '' # so to override None

        start_time = start_time or 0
        if start_time:
            start_time = timegm(start_time.timetuple())

        end_time = end_time or 0
        if end_time:
            end_time = timegm(end_time.timetuple())

        if tags and isinstance(tags, list):
            tags = ", ".join(tags)
        tags = tags or ''

        return self.conn.UpdateFact(fact_id, activity_name, tags, start_time, end_time, category_name, description)


    def get_activities(self, category_id = None):
        """Return activities for category. If category is not specified, will
        return activities that have no category"""
        category_id = category_id or -1
        return self.conn.GetActivities(category_id)

    def get_category_id(self, category_name):
        """returns category id by name"""
        return self.conn.GetCategoryId(category_name)

    def get_activity_by_name(self, activity, category_id = None, ressurect = True):
        """returns activity dict by name and optionally filtering by category.
           if activity is found but is marked as deleted, it will be resurrected
           unless told otherise in the ressurect param
        """
        category_id = category_id or 0
        return self.conn.GetActivityByName(activity, category_id, ressurect)

    # category and activity manipulations (normally just via preferences)
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
