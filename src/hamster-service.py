#!/usr/bin/env python3
# nicked off gwibber

import dbus
import dbus.service

from gi.repository import GLib as glib
from gi.repository import Gio as gio

import hamster
from hamster import logger as hamster_logger
from hamster.lib import i18n
i18n.setup_i18n()  # noqa: E402

from hamster.storage import db
from hamster.lib import datetime as dt
from hamster.lib import default_logger
from hamster.dbus.utilities import (
    DBusMainLoop,
    fact_signature,
    from_dbus_date,
    from_dbus_fact,
    from_dbus_fact_json,
    from_dbus_range,
    to_dbus_fact,
    to_dbus_fact_json
)
from hamster.lib.fact import Fact, FactError

logger = default_logger(__file__)


DBusMainLoop(set_as_default=True)
loop = glib.MainLoop()

if "org.gnome.Hamster" in dbus.SessionBus().list_names():
    print("Found hamster-service already running, exiting")
    quit()


class Storage(dbus.service.Object):
    __dbus_object_path__ = "/org/gnome/Hamster"

    def __init__(self, loop):
        self.bus = dbus.SessionBus()
        bus_name = dbus.service.BusName("org.gnome.Hamster", bus=self.bus)

        dbus.service.Object.__init__(self, bus_name, self.__dbus_object_path__)

        self.storage = db.Storage(unsorted_localized="")
        # append our own fixtures to the database
        self.run_fixtures()

        self.mainloop = loop

        self.__file = gio.File.new_for_path(__file__)
        self.__monitor = self.__file.monitor_file(gio.FileMonitorFlags.WATCH_MOUNTS | \
                                                  gio.FileMonitorFlags.SEND_MOVED,
                                                  None)
        self.__monitor.connect("changed", self._on_us_change)

        self.storage.connect("tags-changed", self._on_storage_tags_changed)
        self.storage.connect("facts-changed", self._on_storage_facts_changed)
        self.storage.connect("activities-changed", self._on_storage_activities_changed)

    def run_fixtures(self):
        """we start with an empty database and then populate with default
           values. This way defaults can be localized!"""

        # defaults
        defaults = [
            (_("Work"), [_("Reading news"),
                         _("Checking stocks"),
                         _("Super secret project X"),
                         _("World domination")]),
            (_("Day-to-day"), [_("Lunch"),
                               _("Watering flowers"),
                               _("Doing handstands")])
        ]
        if not self.storage.get_categories():
            for category, activities in defaults:
                cat_id = self.storage.add_category(category)
                for activity in activities:
                    self.storage.add_activity(activity, cat_id)

    # wrappers needed because GObject signals always pass their owner
    def _on_storage_tags_changed(self, storage):
        self.TagsChanged()

    def _on_storage_facts_changed(self, storage):
        self.FactsChanged()

    def _on_storage_activities_changed(self, storage):
        self.ActivitiesChanged()

    # stop service when we have been updated (will be brought back in next call)
    # anyway. should make updating simpler
    def _on_us_change(self, monitor, gio_file, event_uri, event):
        if event == gio.FileMonitorEvent.CHANGES_DONE_HINT:
            print("`{}` has changed. Quitting!".format(__file__))
            self.Quit()

    @dbus.service.signal("org.gnome.Hamster")
    def TagsChanged(self):
        logger.info("tags changed")

    @dbus.service.signal("org.gnome.Hamster")
    def FactsChanged(self):
        logger.info("facts changed")

    @dbus.service.signal("org.gnome.Hamster")
    def ActivitiesChanged(self):
        logger.info("activities changed")

    # Fate undecided. Is anybody using that ? Not in hamster anyway, as of 2020-02-27.
    # But note the recursive loop. That one has not been fired for a long while...
    @dbus.service.signal("org.gnome.Hamster")
    def ToggleCalled(self): pass
    def toggle_called(self):
        self.toggle_called()

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
    def AddFact(self, fact_str, start_time, end_time, temporary):
        """Add fact specified by a string.

        If the parsed fact has no start, then now is used.
        To fully use the hamster fact parser, as on the cmdline,
        just pass 0 for start_time and end_time.

        Args:
            fact_str (str): string to be parsed.
            start_time (int): Start datetime ovveride timestamp (ignored if 0).
                              -1 means None.
            end_time (int): datetime ovveride timestamp (ignored if 0).
                            -1 means None.
            #temporary (boolean): historical mystery, ignored, but needed to
                                 keep the method signature stable.
                                 Do not forget to pass something (e.g. False)!
        Returns:
            fact id (int), 0 means failure.

        Note: see datetime.utcfromtimestamp documentation
              for the precise meaning of timestamps.
        """
        fact = Fact.parse(fact_str)

        # default value if none found
        if not fact.start_time:
            fact.start_time = dt.datetime.now()

        if start_time == -1:
            fact.start_time = None
        elif start_time != 0:
            fact.start_time = dt.datetime.utcfromtimestamp(start_time)

        if end_time == -1:
            fact.end_time = None
        elif end_time != 0:
            fact.end_time = dt.datetime.utcfromtimestamp(end_time)

        return self.storage.add_fact(fact)


    @dbus.service.method("org.gnome.Hamster", in_signature='s', out_signature='i')
    def AddFactJSON(self, dbus_fact):
        """Add fact given in JSON format.

        This is the preferred method if the fact fields are known separately,
        as activity, category, description and tags are passed "verbatim".
        Only datetimes are interpreted
        (2020-01-20: JSON does not know datetimes).

        Args:
            dbus_fact (str): fact in JSON format (cf. from_dbus_fact_json).

        Returns:
            fact id (int), 0 means failure.
        """
        fact = from_dbus_fact_json(dbus_fact)
        return self.storage.add_fact(fact)


    @dbus.service.method("org.gnome.Hamster",
                         in_signature="si",
                         out_signature='bs')
    def CheckFact(self, dbus_fact, dbus_default_day):
        """Check fact validity.

        Useful to determine in advance whether the fact
        can be included in the database.

        Args:
            dbus_fact (str): fact in JSON format (cf. AddFactJSON)

        Returns:
            success (boolean): True upon success.
            message (str): what's wrong.
        """

        fact = from_dbus_fact_json(dbus_fact)
        dd = from_dbus_date(dbus_default_day)
        try:
            self.storage.check_fact(fact, default_day=dd)
            success = True
            message = ""
        except FactError as error:
            success = False
            message = str(error)
        return success, message


    @dbus.service.method("org.gnome.Hamster",
                         in_signature='i',
                         out_signature=fact_signature)
    def GetFact(self, fact_id):
        """Get fact by id. For output format see GetFacts"""
        fact = self.storage.get_fact(fact_id)
        return to_dbus_fact(fact)


    @dbus.service.method("org.gnome.Hamster",
                         in_signature='i',
                         out_signature="s")
    def GetFactJSON(self, fact_id):
        """Get fact by id.

        Return fact in JSON format (cf. to_dbus_fact_json)
        """
        fact = self.storage.get_fact(fact_id)
        return to_dbus_fact_json(fact)


    @dbus.service.method("org.gnome.Hamster", in_signature='isiib', out_signature='i')
    def UpdateFact(self, fact_id, fact, start_time, end_time, temporary):
        start_time = start_time or None
        if start_time:
            start_time = dt.datetime.utcfromtimestamp(start_time)

        end_time = end_time or None
        if end_time:
            end_time = dt.datetime.utcfromtimestamp(end_time)
        return self.storage.update_fact(fact_id, fact, start_time, end_time, temporary)


    @dbus.service.method("org.gnome.Hamster",
                         in_signature='is',
                         out_signature='i')
    def UpdateFactJSON(self, fact_id, dbus_fact):
        """Update fact.

        Args:
            fact_id (int): fact id in the database.
            dbus_fact (str): new fact content, in JSON format.
        Returns:
            int: new id (0 means failure)
        """
        fact = from_dbus_fact_json(dbus_fact)
        return self.storage.update_fact(fact_id, fact)


    @dbus.service.method("org.gnome.Hamster", in_signature='i')
    def StopTracking(self, end_time):
        """Stops tracking the current activity"""
        end_time = end_time or None
        if end_time:
            end_time = dt.datetime.utcfromtimestamp(end_time)
        return self.storage.stop_tracking(end_time)


    @dbus.service.method("org.gnome.Hamster", in_signature='i')
    def RemoveFact(self, fact_id):
        """Remove fact from storage by it's ID"""
        return self.storage.remove_fact(fact_id)


    @dbus.service.method("org.gnome.Hamster",
                         in_signature='uus',
                         out_signature='a{}'.format(fact_signature))
    def GetFacts(self, start_date, end_date, search_terms):
        """Gets facts between the day of start_date and the day of end_date.
        Parameters:
        i start_date: Seconds since epoch (timestamp). Use 0 for today
        i end_date: Seconds since epoch (timestamp). Use 0 for today
        s search_terms: Bleh. If starts with "not ", the search terms will be reversed
        Returns an array of D-Bus fact structures.

        Legacy. To be superceded by GetFactsJSON at some point.
        """
        #TODO: Assert start > end ?
        start = dt.date.today()
        if start_date:
            start = dt.datetime.utcfromtimestamp(start_date).date()

        end = None
        if end_date:
            end = dt.datetime.utcfromtimestamp(end_date).date()

        return [to_dbus_fact(fact) for fact in self.storage.get_facts(start, end, search_terms)]


    @dbus.service.method("org.gnome.Hamster",
                         in_signature='ss',
                         out_signature='as')
    def GetFactsJSON(self, dbus_range, search_terms):
        """Gets facts between the day of start and the day of end.

        Args:
            dbus_range (str): same format as on the command line.
                              (cf. dt.Range.parse)
            search_terms (str): If starts with "not ",
                                the search terms will be reversed
        Return:
            array of D-Bus facts in JSON format.
            (cf. to_dbus_fact_json)

        This will be the preferred way to get facts.
        """
        range = from_dbus_range(dbus_range)
        return [to_dbus_fact_json(fact)
                for fact in self.storage.get_facts(range, search_terms=search_terms)]


    @dbus.service.method("org.gnome.Hamster", out_signature='a{}'.format(fact_signature))
    def GetTodaysFacts(self):
        """Gets facts of today,
           respecting hamster midnight. See GetFacts for return info.

           Legacy, to be superceded by GetTodaysFactsJSON at some point.
        """
        return [to_dbus_fact(fact) for fact in self.storage.get_todays_facts()]


    @dbus.service.method("org.gnome.Hamster", out_signature='as')
    def GetTodaysFactsJSON(self):
        """Gets facts of the current hamster day.

        Return an array of facts in JSON format.
        """
        return [to_dbus_fact_json(fact) for fact in self.storage.get_todays_facts()]


    # categories
    @dbus.service.method("org.gnome.Hamster", in_signature='s', out_signature = 'i')
    def AddCategory(self, name):
        return self.storage.add_category(name)

    @dbus.service.method("org.gnome.Hamster", in_signature='s', out_signature='i')
    def GetCategoryId(self, category):
        return self.storage.get_category_id(category)

    @dbus.service.method("org.gnome.Hamster", in_signature='is')
    def UpdateCategory(self, id, name):
        self.storage.update_category(id, name)

    @dbus.service.method("org.gnome.Hamster", in_signature='i')
    def RemoveCategory(self, id):
        self.storage.remove_category(id)

    @dbus.service.method("org.gnome.Hamster", out_signature='a(is)')
    def GetCategories(self):
        return [(category['id'], category['name']) for category in self.storage.get_categories()]


    # activities
    @dbus.service.method("org.gnome.Hamster", in_signature='si', out_signature = 'i')
    def AddActivity(self, name, category_id):
        return self.storage.add_activity(name, category_id)

    @dbus.service.method("org.gnome.Hamster", in_signature='isi')
    def UpdateActivity(self, id, name, category_id):
        self.storage.update_activity(id, name, category_id)

    @dbus.service.method("org.gnome.Hamster", in_signature='i')
    def RemoveActivity(self, id):
        return self.storage.remove_activity(id)

    @dbus.service.method("org.gnome.Hamster", in_signature='i', out_signature='a(isis)')
    def GetCategoryActivities(self, category_id):
        return [(row['id'],
                 row['name'],
                 row['category_id'],
                 row['category'] or '') for row in
                      self.storage.get_category_activities(category_id = category_id)]


    @dbus.service.method("org.gnome.Hamster", in_signature='s', out_signature='a(ss)')
    def GetActivities(self, search = ""):
        return [(row['name'], row['category'] or '') for row in self.storage.get_activities(search)]


    @dbus.service.method("org.gnome.Hamster", in_signature='ii', out_signature = 'b')
    def ChangeCategory(self, id, category_id):
        return self.storage.change_category(id, category_id)


    @dbus.service.method("org.gnome.Hamster", in_signature='sib', out_signature='a{sv}')
    def GetActivityByName(self, activity, category_id, resurrect = True):
        category_id = category_id or None
        if activity:
            return dict(self.storage.get_activity_by_name(activity, category_id, resurrect) or {})
        else:
            return {}

    # tags
    @dbus.service.method("org.gnome.Hamster", in_signature='b', out_signature='a(isb)')
    def GetTags(self, only_autocomplete):
        return [(tag['id'], tag['name'], tag['autocomplete']) for tag in self.storage.get_tags(only_autocomplete)]


    @dbus.service.method("org.gnome.Hamster", in_signature='as', out_signature='a(isb)')
    def GetTagIds(self, tags):
        return [(tag['id'], tag['name'], tag['autocomplete']) for tag in self.storage.get_tag_ids(tags)]


    @dbus.service.method("org.gnome.Hamster", in_signature='s')
    def SetTagsAutocomplete(self, tags):
        self.storage.update_autocomplete_tags(tags)


    @dbus.service.method("org.gnome.Hamster", out_signature='s')
    def Version(self):
        return hamster.__version__


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Hamster time tracker D-Bus service")

    # cf. https://stackoverflow.com/a/28611921/3565696
    parser.add_argument("--log", dest="log_level",
                        choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
                        default='WARNING',
                        help="Set the logging level (default: %(default)s)")

    args = parser.parse_args()

    # logger for current script
    logger.setLevel(args.log_level)
    # hamster_logger for the rest
    hamster_logger.setLevel(args.log_level)

    print("hamster-service up")
    storage = Storage(loop)
    loop.run()
