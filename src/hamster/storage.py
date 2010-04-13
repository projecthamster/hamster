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


    def run_fixtures(self):
        pass

    @dbus.service.signal("org.gnome.Hamster")
    def TagsChanged(self): pass

    @dbus.service.signal("org.gnome.Hamster")
    def FactsChanged(self): pass

    @dbus.service.signal("org.gnome.Hamster")
    def ActivitiesChanged(self): pass

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


    # facts

    @dbus.service.method("org.gnome.Hamster", in_signature='ssiiss', out_signature='i')
    def AddFact(self, activity_name, tags, start_time, end_time,
                                      category_name = None, description = None):

        if start_time:
            start_time = dt.datetime.utcfromtimestamp(start_time)
        else:
            start_time = None

        if end_time:
            end_time = dt.datetime.utcfromtimestamp(end_time)
        else:
            end_time = None

        self.start_transaction()
        result = self.__add_fact(activity_name, tags, start_time, end_time, category_name, description)
        self.end_transaction()

        if result:
            self.FactsChanged()
        return result


    @dbus.service.method("org.gnome.Hamster", in_signature='i', out_signature='(iiissisasii)')
    def GetFact(self, fact_id):
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
        fact = dict(self.__get_fact(fact_id))
        fact['date'] = fact['start_time'].date()
        fact['delta'] = dt.timedelta()
        return to_dbus_fact(fact)


    @dbus.service.method("org.gnome.Hamster", in_signature='issiiss', out_signature='i')
    def UpdateFact(self, fact_id, activity_name, tags, start_time, end_time, category_name = None, description = None):
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
        result = self.__add_fact(activity_name, tags, start_time, end_time, category_name, description)
        self.end_transaction()

        if result:
            self.FactsChanged()
        return result


    @dbus.service.method("org.gnome.Hamster")
    def StopTracking(self, end_time):
        """Stops tracking the current activity"""
        end_time = dt.datetime.utcfromtimestamp(end_time)

        fact = self.__get_last_activity()
        if fact:
            self.__touch_fact(fact, end_time)
            self.FactsChanged()


    @dbus.service.method("org.gnome.Hamster", in_signature='i')
    def RemoveFact(self, fact_id):
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
        if start_date:
            start = dt.datetime.utcfromtimestamp(start_date).date()
        else:
            start = dt.date.today()

        if end_date:
            end = dt.datetime.utcfromtimestamp(end_date).date()
        else:
            end = dt.date.today()

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

    @dbus.service.method("org.gnome.Hamster", in_signature='s', out_signature='a{sv}')
    def GetCategoryByName(self, category):
        return dict(self.__get_category_by_name(category))

    @dbus.service.method("org.gnome.Hamster", in_signature='is')
    def UpdateCategory(self, id, name):
        self.__update_category(id, name)
        self.ActivitiesChanged()


    @dbus.service.method("org.gnome.Hamster", in_signature='i')
    def RemoveCategory(self, id):
        self.__remove_category(id)
        self.ActivitiesChanged()


    @dbus.service.method("org.gnome.Hamster", out_signature='aa{sv}')
    def GetCategories(self):
        res = []
        for category in self.__get_category_list():
            category = dict(category)
            category['color_code'] = category['color_code'] or ''
            res.append(category)


        return res


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

    @dbus.service.method("org.gnome.Hamster", out_signature='a{sv}')
    def GetLastActivity(self):
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
        return to_dbus_fact(self__.get_last_activity())


    @dbus.service.method("org.gnome.Hamster", in_signature='i', out_signature='aa{sv}')
    def GetActivities(self, category_id = None):
        if not category_id or category_id == -1:
            category_id = None

        res = []
        for activity in self.__get_activities(category_id = category_id):
            activity = dict(activity)
            activity['category'] = activity['category'] or ''

            res.append(activity)

        return res


    @dbus.service.method("org.gnome.Hamster", in_signature='s', out_signature='aa{sv}')
    def GetAutocompleteActivities(self, search = ""):
        res = []
        for activity in self.__get_autocomplete_activities(search):
            activity = dict(activity)
            activity['category'] = activity['category'] or ''
            res.append(activity)

        return res



    @dbus.service.method("org.gnome.Hamster", in_signature='iib')
    def MoveActivity(self, source_id, target_order, insert_after = True):
        self.__move_activity(source_id, target_order, insert_after)
        self.ActivitiesChanged()


    @dbus.service.method("org.gnome.Hamster", in_signature='ii', out_signature = 'b')
    def ChangeCategory(self, id, category_id):
        changed = self.__change_category(id, category_id)
        if changed:
            self.ActivitiesChanged()
        return changed


    @dbus.service.method("org.gnome.Hamster", in_signature='iiii')
    def SwapActivities(self, id1, priority1, id2, priority2):
        self.__swap_activities(id1, priority1, id2, priority2)
        self.ActivitiesChanged()


    @dbus.service.method("org.gnome.Hamster", in_signature='sib', out_signature='a{sv}')
    def GetActivityByName(self, activity, category_id, ressurect = True):
        category_id = category_id or None

        if activity:
            return dict(self.__get_activity_by_name(activity, category_id, ressurect))
        else:
            return {}

    # tags
    @dbus.service.method("org.gnome.Hamster", in_signature='b', out_signature='aa{sv}')
    def GetTags(self, autocomplete = None):
        return [dict(tag) for tag in self.__get_tags(autocomplete)]


    @dbus.service.method("org.gnome.Hamster", in_signature='as', out_signature='aa{sv}')
    def GetTagIds(self, tags):
        tags, new_added = self.__get_tag_ids(tags)
        if new_added:
            self.TagsChanged()
        return [dict(tag) for tag in tags]


    @dbus.service.method("org.gnome.Hamster", in_signature='as')
    def SetTagsAutocomplete(self, tags):
        changes = self.__update_autocomplete_tags(tags)
        if changes:
            self.TagsChanged()
