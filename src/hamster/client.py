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


import dbus
import logging
logger = logging.getLogger(__name__)   # noqa: E402
import sys

from calendar import timegm
from distutils.version import LooseVersion
from gi.repository import GObject as gobject
from textwrap import dedent

import hamster
from hamster.lib.dbus import (
    DBusMainLoop,
    from_dbus_fact_json,
    to_dbus_date,
    to_dbus_fact,
    to_dbus_fact_json,
    to_dbus_range,
    )
from hamster.lib.fact import Fact, FactError
from hamster.lib import datetime as dt


# bug fixed in dbus-python 1.2.14 (released on 2019-11-25)
assert not (
    sys.version_info >= (3, 8)
    and LooseVersion(dbus.__version__) < LooseVersion("1.2.14")
    ), """python3.8 changed str(<dbus integers>).
       That broke hamster (https://github.com/projecthamster/hamster/issues/477).
       Please upgrade to dbus-python >= 1.2.14.
    """


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
        "tags-changed": (gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, ()),
        "facts-changed": (gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, ()),
        "activities-changed": (gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, ()),
        "toggle-called": (gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        DBusMainLoop(set_as_default=True)
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
            server_version = self._connection.Version()
            client_version = hamster.__version__
            if server_version != client_version:
                logger.warning(dedent(
                    """\
                    Server and client version mismatch:
                        server: {}
                        client: {}

                        This is sometimes used during bisections,
                        but generally calls for trouble.

                        Remember to kill hamster daemons after any version change
                        (this is safe):
                        pkill -f hamster-service
                        pkill -f hamster-windows-service
                        see also:
                        https://github.com/projecthamster/hamster#kill-hamster-daemons
                    """.format(server_version, client_version)
                )
                )
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
        return [from_dbus_fact_json(fact) for fact in self.conn.GetTodaysFactsJSON()]

    def get_facts(self, start, end=None, search_terms=""):
        """Returns facts for the time span matching the optional filter criteria.
           In search terms comma (",") translates to boolean OR and space (" ")
           to boolean AND.
           Filter is applied to tags, categories, activity names and description
        """
        range = dt.Range.from_start_end(start, end)
        dbus_range = to_dbus_range(range)
        return [from_dbus_fact_json(fact)
                for fact in self.conn.GetFactsJSON(dbus_range, search_terms)]

    def get_activities(self, search=""):
        """returns list of activities name matching search criteria.
           results are sorted by most recent usage.
           search is case insensitive
        """
        return self._to_dict(('name', 'category'), self.conn.GetActivities(search))

    def get_ext_activities(self, search=""):
        """returns list of activities name matching search criteria.
           results are sorted by most recent usage.
           search is case insensitive
        """
        return self._to_dict(('name', 'category'), self.conn.GetExtActivities(search))

    def export_fact(self, fact_id):
        """export facts to external source.
           :returns true if fact was exported
        """
        return self.conn.ExportFact(fact_id)

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
        return from_dbus_fact_json(self.conn.GetFactJSON(id))

    def check_fact(self, fact, default_day=None):
        """Check Fact validity for inclusion in the storage.

        default_day (date): Default hamster day,
                            used to simplify some hint messages
                            (remove unnecessary dates).
                            None is safe (always show dates).
        """
        if not fact.start_time:
            # Do not even try to pass fact through D-Bus as
            # conversions would fail in this case.
            raise FactError("Missing start time")
        dbus_fact = to_dbus_fact_json(fact)
        dbus_day = to_dbus_date(default_day)
        success, message = self.conn.CheckFact(dbus_fact, dbus_day)
        if not success:
            raise FactError(message)
        return success, message

    def add_fact(self, fact, temporary_activity = False):
        """Add fact (Fact)."""
        assert fact.activity, "missing activity"

        if not fact.start_time:
            logger.info("Adding fact without any start_time is deprecated")
            fact.start_time = dt.datetime.now()

        dbus_fact = to_dbus_fact_json(fact)
        new_id = self.conn.AddFactJSON(dbus_fact)

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

        dbus_fact = to_dbus_fact_json(fact)
        new_id = self.conn.UpdateFactJSON(fact_id, dbus_fact)

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
