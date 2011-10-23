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

import dbus, dbus.service
import datetime as dt
from calendar import timegm
import gio
from lib import stuff

def to_dbus_fact(fact):
    """Perform the conversion between fact database query and
    dbus supported data types
    """
    return (fact['id'],
            timegm(fact['start_time'].timetuple()),
            timegm(fact['end_time'].timetuple()) if fact['end_time'] else 0,
            fact['description'] or '',
            fact['name'] or '',
            fact['activity_id'] or 0,
            fact['category'] or '',
            dbus.Array(fact['tags'], signature = 's'),
            timegm(fact['date'].timetuple()),
            fact['delta'].days * 24 * 60 * 60 + fact['delta'].seconds)


class Storage(dbus.service.Object):
    __dbus_object_path__ = "/org/gnome/Hamster"

    def __init__(self, loop):
        self.bus = dbus.SessionBus()
        bus_name = dbus.service.BusName("org.gnome.Hamster", bus=self.bus)
        dbus.service.Object.__init__(self, bus_name, self.__dbus_object_path__)
        self.mainloop = loop

        self.__file = gio.File(__file__)
        self.__monitor = self.__file.monitor_file()
        self.__monitor.connect("changed", self._on_us_change)

    # stop service when we have been updated (will be brought back in next call)
    # anyway. should make updating simpler
    def _on_us_change(self, monitor, gio_file, event_uri, event):
        if event == gio.FILE_MONITOR_EVENT_CHANGES_DONE_HINT:
            print "`%s` has changed. Quitting!" % __file__
            self.Quit()

    def run_fixtures(self):
        pass

    @dbus.service.signal("org.gnome.Hamster")
    def TagsChanged(self): pass

    @dbus.service.signal("org.gnome.Hamster")
    def FactsChanged(self): pass

    @dbus.service.signal("org.gnome.Hamster")
    def ActivitiesChanged(self): pass

    @dbus.service.signal("org.gnome.Hamster")
    def ToggleCalled(self): pass

    def dispatch_overwrite(self):
        self.TagsChanged()
        self.FactsChanged()
        self.ActivitiesChanged()



    @dbus.service.method("org.gnome.Hamster")
    def Quit(self):
        """
        Shutdown the service
        example:
            import dbus
            obj = dbus.SessionBus().get_object("org.gnome.Hamster", "/org/gnome/Hamster")
            service = dbus.Interface(obj, "org.gnome.Hamster")
            service.Quit()
        """
        #log.logger.info("Hamster Service is being shutdown")
        self.mainloop.quit()


    @dbus.service.method("org.gnome.Hamster")
    def Toggle(self):
        """Toggle visibility of the main application window.
           If several instances are available, it will toggle them all.
        """
        #log.logger.info("Hamster Service is being shutdown")
        self.ToggleCalled()

    # facts
    @dbus.service.method("org.gnome.Hamster", in_signature='siib', out_signature='i')
    def AddFact(self, fact, start_time, end_time, temporary = False):
        start_time = dt.datetime.utcfromtimestamp(start_time) if start_time else None
        end_time = dt.datetime.utcfromtimestamp(end_time) if end_time else None

        fact = stuff.Fact(fact, start_time = start_time, end_time = end_time)
        start_time = fact.start_time or dt.datetime.now().replace(second = 0, microsecond = 0)

        self.start_transaction()
        result = self.__add_fact(fact.serialized_name(), start_time, end_time, temporary)
        self.end_transaction()

        if result:
            self.FactsChanged()
        return result or 0


    @dbus.service.method("org.gnome.Hamster", in_signature='i', out_signature='(iiissisasii)')
    def GetFact(self, fact_id):
        """Get fact by id. For output format see GetFacts"""
        fact = dict(self.__get_fact(fact_id))
        fact['date'] = fact['start_time'].date()
        fact['delta'] = dt.timedelta()
        return to_dbus_fact(fact)


    @dbus.service.method("org.gnome.Hamster", in_signature='isiib', out_signature='i')
    def UpdateFact(self, fact_id, fact, start_time, end_time, temporary = False):
        if start_time:
            start_time = dt.datetime.utcfromtimestamp(start_time)
        else:
            start_time = None

        if end_time:
            end_time = dt.datetime.utcfromtimestamp(end_time)
        else:
            end_time = None

        self.start_transaction()
        self.__remove_fact(fact_id)
        result = self.__add_fact(fact, start_time, end_time, temporary)

        self.end_transaction()

        if result:
            self.FactsChanged()
        return result


    @dbus.service.method("org.gnome.Hamster")
    def StopTracking(self, end_time):
        """Stops tracking the current activity"""
        end_time = dt.datetime.utcfromtimestamp(end_time)

        facts = self.__get_todays_facts()
        if facts:
            self.__touch_fact(facts[-1], end_time)
            self.FactsChanged()


    @dbus.service.method("org.gnome.Hamster", in_signature='i')
    def RemoveFact(self, fact_id):
        """Remove fact from storage by it's ID"""
        self.start_transaction()
        fact = self.__get_fact(fact_id)
        if fact:
            self.__remove_fact(fact_id)
            self.FactsChanged()
        self.end_transaction()


    @dbus.service.method("org.gnome.Hamster", in_signature='uus', out_signature='a(iiissisasii)')
    def GetFacts(self, start_date, end_date, search_terms):
        """Gets facts between the day of start_date and the day of end_date.
        Parameters:
        i start_date: Seconds since epoch (timestamp). Use 0 for today
        i end_date: Seconds since epoch (timestamp). Use 0 for today
        s search_terms: Bleh
        Returns Array of fact where fact is struct of:
            i  id
            i  start_time
            i  end_time
            s  description
            s  activity name
            i  activity id
            i  category name
            as List of fact tags
            i  date
            i  delta
        """
        #TODO: Assert start > end ?
        start = dt.date.today()
        if start_date:
            start = dt.datetime.utcfromtimestamp(start_date).date()

        end = None
        if end_date:
            end = dt.datetime.utcfromtimestamp(end_date).date()

        return [to_dbus_fact(fact) for fact in self.__get_facts(start, end, search_terms)]


    @dbus.service.method("org.gnome.Hamster", out_signature='a(iiissisasii)')
    def GetTodaysFacts(self):
        """Gets facts of today, respecting hamster midnight. See GetFacts for
        return info"""
        return [to_dbus_fact(fact) for fact in self.__get_todays_facts()]


    # categories

    @dbus.service.method("org.gnome.Hamster", in_signature='s', out_signature = 'i')
    def AddCategory(self, name):
        res = self.__add_category(name)
        self.ActivitiesChanged()
        return res

    @dbus.service.method("org.gnome.Hamster", in_signature='s', out_signature='i')
    def GetCategoryId(self, category):
        return self.__get_category_id(category)

    @dbus.service.method("org.gnome.Hamster", in_signature='is')
    def UpdateCategory(self, id, name):
        self.__update_category(id, name)
        self.ActivitiesChanged()


    @dbus.service.method("org.gnome.Hamster", in_signature='i')
    def RemoveCategory(self, id):
        self.__remove_category(id)
        self.ActivitiesChanged()


    @dbus.service.method("org.gnome.Hamster", out_signature='a(is)')
    def GetCategories(self):
        return [(category['id'], category['name']) for category in self.__get_categories()]


    # activities

    @dbus.service.method("org.gnome.Hamster", in_signature='si', out_signature = 'i')
    def AddActivity(self, name, category_id = -1):
        new_id = self.__add_activity(name, category_id)
        self.ActivitiesChanged()
        return new_id


    @dbus.service.method("org.gnome.Hamster", in_signature='isi')
    def UpdateActivity(self, id, name, category_id):
        self.__update_activity(id, name, category_id)
        self.ActivitiesChanged()



    @dbus.service.method("org.gnome.Hamster", in_signature='i')
    def RemoveActivity(self, id):
        result = self.__remove_activity(id)
        self.ActivitiesChanged()
        return result

    @dbus.service.method("org.gnome.Hamster", in_signature='i', out_signature='a(isis)')
    def GetCategoryActivities(self, category_id = -1):

        return [(row['id'],
                 row['name'],
                 row['category_id'],
                 row['name'] or '') for row in
                      self.__get_category_activities(category_id = category_id)]


    @dbus.service.method("org.gnome.Hamster", in_signature='s', out_signature='a(ss)')
    def GetActivities(self, search = ""):
        return [(row['name'], row['category'] or '') for row in self.__get_activities(search)]


    @dbus.service.method("org.gnome.Hamster", in_signature='ii', out_signature = 'b')
    def ChangeCategory(self, id, category_id):
        changed = self.__change_category(id, category_id)
        if changed:
            self.ActivitiesChanged()
        return changed


    @dbus.service.method("org.gnome.Hamster", in_signature='sib', out_signature='a{sv}')
    def GetActivityByName(self, activity, category_id, resurrect = True):
        category_id = category_id or None

        if activity:
            return dict(self.__get_activity_by_name(activity, category_id, resurrect) or {})
        else:
            return {}

    # tags
    @dbus.service.method("org.gnome.Hamster", in_signature='b', out_signature='a(isb)')
    def GetTags(self, only_autocomplete):
        return [(tag['id'], tag['name'], tag['autocomplete']) for tag in self.__get_tags(only_autocomplete)]


    @dbus.service.method("org.gnome.Hamster", in_signature='as', out_signature='a(isb)')
    def GetTagIds(self, tags):
        tags, new_added = self.__get_tag_ids(tags)
        if new_added:
            self.TagsChanged()
        return [(tag['id'], tag['name'], tag['autocomplete']) for tag in tags]


    @dbus.service.method("org.gnome.Hamster", in_signature='s')
    def SetTagsAutocomplete(self, tags):
        changes = self.__update_autocomplete_tags(tags)
        if changes:
            self.TagsChanged()
