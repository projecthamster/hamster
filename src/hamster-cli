#!/usr/bin/env python3
# - coding: utf-8 -

# Copyright (C) 2010 Matías Ribecky <matias at mribecky.com.ar>
# Copyright (C) 2010-2012 Toms Bauģis <toms.baugis@gmail.com>
# Copyright (C) 2012 Ted Smith <tedks at cs.umd.edu>

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

'''A script to control the applet from the command line.'''

import sys, os
import argparse
import re
import datetime as dt

from hamster import client, reports
from hamster import logger as hamster_logger
from hamster.lib import default_logger, Fact, stuff
from hamster.lib.parsing import parse_datetime_range


logger = default_logger(__file__)


def word_wrap(line, max_len):
    """primitive word wrapper"""
    lines = []
    cur_line, cur_len = "", 0
    for word in line.split():
        if len("%s %s" % (cur_line, word)) < max_len:
            cur_line = ("%s %s" % (cur_line, word)).strip()
        else:
            if cur_line:
                lines.append(cur_line)
            cur_line = word
    if cur_line:
        lines.append(cur_line)
    return lines


def fact_dict(fact_data, with_date):
    fact = {}
    if with_date:
        fmt = '%Y-%m-%d %H:%M'
    else:
        fmt = '%H:%M'

    fact['start'] = fact_data.start_time.strftime(fmt)
    if fact_data.end_time:
        fact['end'] = fact_data.end_time.strftime(fmt)
    else:
        end_date = stuff.hamster_now()
        fact['end'] = ''

    fact['duration'] = stuff.format_duration(fact_data.delta)

    fact['activity'] = fact_data.activity
    fact['category'] = fact_data.category
    if fact_data.tags:
        fact['tags'] = ' '.join('#%s' % tag for tag in fact_data.tags)
    else:
        fact['tags'] = ''

    fact['description'] = fact_data.description

    return fact


class HamsterClient(object):
    '''The main application.'''
    def __init__(self):
        self.storage = client.Storage()


    def _launch_window(self, window_name):
        try:
            from hamster import defs
            running_installed = True
        except:
            running_installed = False

        if running_installed:
            import dbus
            bus = dbus.SessionBus()
            server = bus.get_object("org.gnome.Hamster.WindowServer",
                                    "/org/gnome/Hamster/WindowServer")
            getattr(server, window_name)()
        else:
            print("Running in devel mode")
            from gi.repository import Gtk as gtk
            from hamster.lib.configuration import dialogs
            getattr(dialogs, window_name).show()
            gtk.main()

    def overview(self, *args):
        self._launch_window("overview")

    def about(self, *args):
        self._launch_window("about")

    def prefs(self, *args):
        self._launch_window("prefs")

    def add(self, *args):
        self._launch_window("edit")


    def assist(self, *args):
        assist_command = args[0] if args else ""

        if assist_command == "start":
            hamster_client._activities(sys.argv[-1])
        elif assist_command == "export":
            formats = "html tsv xml ical".split()
            chosen = sys.argv[-1]
            formats = [f for f in formats if not chosen or f.startswith(chosen)]
            print("\n".join(formats))


    def toggle(self):
        self.storage.toggle()

    def track(self, *args):
        """same as start"""
        self.start(*args)


    def start(self, *args):
        '''Start a new activity.'''
        if not args:
            print("Error: please specify activity")
            return

        fact = Fact.parse(" ".join(args), range_pos="tail")
        if fact.start_time is None:
            fact.start_time = stuff.hamster_now()
        self.storage.add_fact(fact)

    def stop(self, *args):
        '''Stop tracking the current activity.'''
        self.storage.stop_tracking()


    def export(self, *args):
        args = args or []
        export_format, start_time, end_time = "html", None, None
        if args:
            export_format = args[0]
        start_time, end_time, _ = parse_datetime_range(" ".join(args[1:]))

        start_time = start_time or dt.datetime.combine(dt.date.today(), dt.time())
        end_time = end_time or start_time.replace(hour=23, minute=59, second=59)
        facts = self.storage.get_facts(start_time, end_time)

        writer = reports.simple(facts, start_time.date(), end_time.date(), export_format)


    def _activities(self, search=""):
        '''Print the names of all the activities.'''
        if "@" in search:
            activity, category = search.split("@")
            for cat in self.storage.get_categories():
                if not category or cat['name'].lower().startswith(category.lower()):
                    print("{}@{}".format(activity, cat['name']))
        else:
            for activity in self.storage.get_activities(search):
                print(activity['name'])
                if activity['category']:
                    print("{}@{}".format(activity['name'], activity['category']))


    def activities(self, *args):
        '''Print the names of all the activities.'''
        search = args[0] if args else ""
        for activity in self.storage.get_activities(search):
            print("{}@{}".format(activity['name'], activity['category']))

    def categories(self, *args):
        '''Print the names of all the categories.'''
        for category in self.storage.get_categories():
            print(category['name'])


    def list(self, *times):
        """list facts within a date range"""
        start_time, end_time, _ = parse_datetime_range(" ".join(times or []))

        start_time = start_time or dt.datetime.combine(dt.date.today(), dt.time())
        end_time = end_time or start_time.replace(hour=23, minute=59, second=59)
        self._list(start_time, end_time)


    def current(self, *args):
        """prints current activity. kinda minimal right now"""
        facts = self.storage.get_todays_facts()
        if facts and not facts[-1].end_time:
            print("{} {}".format(str(facts[-1]).strip(),
                                 stuff.format_duration(facts[-1].delta, human=False)))
        else:
            print((_("No activity")))


    def search(self, *args):
        """search for activities by name and optionally within a date range"""
        args = args or []
        search = ""
        if args:
            search = args[0]

        start_time, end_time, _ = parse_datetime_range(" ".join(args[1:]))

        start_time = start_time or dt.datetime.combine(dt.date.today(), dt.time())
        end_time = end_time or start_time.replace(hour=23, minute=59, second=59)
        self._list(start_time, end_time, search)


    def _list(self, start_time, end_time, search=""):
        """Print a listing of activities"""
        facts = self.storage.get_facts(start_time, end_time, search)


        headers = {'activity': _("Activity"),
                   'category': _("Category"),
                   'tags': _("Tags"),
                   'description': _("Description"),
                   'start': _("Start"),
                   'end': _("End"),
                   'duration': _("Duration")}


        # print date if it is not the same day
        print_with_date = start_time.date() != end_time.date()

        cols = 'start', 'end', 'duration', 'activity', 'category'


        widths = dict([(col, len(headers[col])) for col in cols])
        for fact in facts:
            fact = fact_dict(fact, print_with_date)
            for col in cols:
                widths[col] = max(widths[col], len(fact[col]))

        cols = ["{{{col}: <{len}}}".format(col=col, len=widths[col]) for col in cols]
        fact_line = " | ".join(cols)

        row_width = sum(val + 3 for val in list(widths.values()))

        print()
        print(fact_line.format(**headers))
        print("-" * min(row_width, 80))

        by_cat = {}
        for fact in facts:
            cat = fact.category or _("Unsorted")
            by_cat.setdefault(cat, dt.timedelta(0))
            by_cat[cat] += fact.delta

            pretty_fact = fact_dict(fact, print_with_date)
            print(fact_line.format(**pretty_fact))

            if pretty_fact['description']:
                for line in word_wrap(pretty_fact['description'], 76):
                    print("    {}".format(line))

            if pretty_fact['tags']:
                for line in word_wrap(pretty_fact['tags'], 76):
                    print("    {}".format(line))

        print("-" * min(row_width, 80))

        cats = []
        total_duration = dt.timedelta()
        for cat, duration in sorted(by_cat.items(), key=lambda x: x[1], reverse=True):
            cats.append("{}: {}".format(cat, stuff.format_duration(duration)))
            total_duration += duration

        for line in word_wrap(", ".join(cats), 80):
            print(line)
        print("Total: ", stuff.format_duration(total_duration))

        print()




if __name__ == '__main__':
    from hamster.lib import i18n
    i18n.setup_i18n()

    usage = _(
"""
Actions:
    * start / track <activity> [start-time] [end-time]: Track an activity
    * stop: Stop tracking current activity.
    * list [start-date [end-date]]: List activities
    * search [terms] [start-date [end-date]]: List activities matching a search
      term
    * export [html|tsv|ical|xml] [start-date [end-date]]: Export activities with
      the specified format
    * current: Print current activity
    * activities: List all the activities names, one per line.
    * categories: List all the categories names, one per line.

    * overview / prefs / add / about: launch specific window

Time formats:
    * 'YYYY-MM-DD hh:mm': If start-date is missing, it will default to today.
      If end-date is missing, it will default to start-date.
    * '-minutes': Relative time in minutes from the current date and time.
Note:
    * For list/search/export a "hamster day" starts at the time set in the
      preferences (default 05:00) and ends one minute earlier the next day.
      Activities are reported for each "hamster day" in the interval.

Example usage:
    hamster start bananas -20
        start activity 'bananas' with start time 20 minutes ago

    hamster search pancakes 2012-08-01 2012-08-30
        look for an activity matching terms 'pancakes` between 1st and 30st
        August 2012. Will check against activity, category, description and tags
""")
    hamster_client = HamsterClient()

    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c

    parser = argparse.ArgumentParser(
        description="Time tracking utility",
        epilog=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # cf. https://stackoverflow.com/a/28611921/3565696
    parser.add_argument("--log", dest="log_level",
                        choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
                        default='WARNING',
                        help="Set the logging level (default: %(default)s)")
    parser.add_argument("action", nargs="?", default="overview")
    parser.add_argument('action_args', nargs=argparse.REMAINDER, default=[])

    args = parser.parse_args()

    # logger for current script
    logger.setLevel(args.log_level)
    # hamster_logger for the rest
    hamster_logger.setLevel(args.log_level)

    command = args.action
    if hasattr(hamster_client, command):
        getattr(hamster_client, command)(*args.action_args)
    else:
        sys.exit(usage % {'prog': sys.argv[0]})
