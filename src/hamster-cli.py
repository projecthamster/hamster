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

import gi
gi.require_version('Gdk', '3.0')  # noqa: E402
gi.require_version('Gtk', '3.0')  # noqa: E402
from gi.repository import GLib as glib
from gi.repository import Gdk as gdk
from gi.repository import Gtk as gtk
from gi.repository import Gio as gio
from gi.repository import GLib as glib

import hamster

from hamster import client, reports
from hamster import logger as hamster_logger
from hamster.about import About
from hamster.edit_activity import CustomFactController
from hamster.overview import Overview
from hamster.preferences import PreferencesEditor
from hamster.lib import default_logger, stuff
from hamster.lib import datetime as dt
from hamster.lib.fact import Fact


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
        end_date = dt.datetime.now()
        fact['end'] = ''

    fact['duration'] = fact_data.delta.format()

    fact['activity'] = fact_data.activity
    fact['category'] = fact_data.category
    if fact_data.tags:
        fact['tags'] = ' '.join('#%s' % tag for tag in fact_data.tags)
    else:
        fact['tags'] = ''

    fact['description'] = fact_data.description

    return fact


class Hamster(gtk.Application):
    """Hamster gui.

    Actions should eventually be accessible via Gio.DBusActionGroup
    with the 'org.gnome.Hamster.GUI' id.
    but that is still experimental, the actions API is subject to change.
    Discussion with "external" developers welcome !
    The separate dbus org.gnome.Hamster.WindowServer
    is still the stable recommended way to show windows for now.
    """

    def __init__(self):
        # inactivity_timeout: How long (ms) the service should stay alive
        #                     after all windows have been closed.
        gtk.Application.__init__(self,
                                 application_id="org.gnome.Hamster.GUI",
                                 #inactivity_timeout=10000,
                                 register_session=True)

        self.about_controller = None  # 'about' window controller
        self.fact_controller = None  # fact window controller
        self.overview_controller = None  # overview window controller
        self.preferences_controller = None  # settings window controller

        self.connect("startup", self.on_startup)
        self.connect("activate", self.on_activate)

        # we need them before the startup phase
        # so register/activate_action work before the app is ran.
        # cf. https://gitlab.gnome.org/GNOME/glib/blob/master/gio/tests/gapplication-example-actions.c
        self.add_actions()

    def add_actions(self):
        # most actions have no parameters
        # for type "i", use Variant.new_int32() and .get_int32() to pack/unpack
        for name in ("about", "add", "clone", "edit", "overview", "preferences"):
            data_type = glib.VariantType("i") if name in ("edit", "clone") else None
            action = gio.SimpleAction.new(name, data_type)
            action.connect("activate", self.on_activate_window)
            self.add_action(action)

        action = gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_activate_quit)
        self.add_action(action)

    def on_activate(self, data=None):
        logger.debug("activate")
        if not self.get_windows():
            self.activate_action("overview")

    def on_activate_window(self, action=None, data=None):
        self._open_window(action.get_name(), data)

    def on_activate_quit(self, data=None):
        self.on_activate_quit()

    def on_startup(self, data=None):
        logger.debug("startup")
        # Must be the same as application_id. Won't be required with gtk4.
        glib.set_prgname(self.get_application_id())
        # localized name, but let's keep it simple.
        glib.set_application_name("Hamster")

    def _open_window(self, name, data=None):
        logger.debug("opening '{}'".format(name))

        if name == "about":
            if not self.about_controller:
                # silence warning "GtkDialog mapped without a transient parent"
                # https://stackoverflow.com/a/38408127/3565696
                _dummy = gtk.Window()
                self.about_controller = About(parent=_dummy)
                logger.debug("new About")
            controller = self.about_controller
        elif name in ("add", "clone", "edit"):
            if self.fact_controller:
                # Something is already going on, with other arguments, present it.
                # Or should we just discard the forgotten one ?
                logger.warning("Fact controller already active. Please close first.")
            else:
                fact_id = data.get_int32() if data else None
                self.fact_controller = CustomFactController(name, fact_id=fact_id)
                logger.debug("new CustomFactController")
            controller = self.fact_controller
        elif name == "overview":
            if not self.overview_controller:
                self.overview_controller = Overview()
                logger.debug("new Overview")
            controller = self.overview_controller
        elif name == "preferences":
            if not self.preferences_controller:
                self.preferences_controller = PreferencesEditor()
                logger.debug("new PreferencesEditor")
            controller = self.preferences_controller

        window = controller.window
        if window not in self.get_windows():
            self.add_window(window)
            logger.debug("window added")

        # Essential for positioning on wayland.
        # This should also select the correct window type if unset yet.
        # https://specifications.freedesktop.org/wm-spec/wm-spec-1.3.html
        if name != "overview" and self.overview_controller:
            window.set_transient_for(self.overview_controller.window)
            # so the dialog appears on top of the transient-for:
            window.set_type_hint(gdk.WindowTypeHint.DIALOG)
        else:
            # toplevel
            window.set_transient_for(None)

        controller.present()
        logger.debug("window presented")

    def present_fact_controller(self, action, fact_id=0):
        """Present the fact controller window to add, clone or edit a fact.

        Args:
            action (str): "add", "clone" or "edit"
        """
        assert action in ("add", "clone", "edit")
        if action in ("clone", "edit"):
            action_data = glib.Variant.new_int32(int(fact_id))
        else:
            action_data = None
        # always open dialogs through actions,
        # both for consistency, and to reduce the paths to test.
        app.activate_action(action, action_data)

class HamsterCli(object):
    """Command line interface."""

    def __init__(self):
        self.storage = client.Storage()


    def assist(self, *args):
        assist_command = args[0] if args else ""

        if assist_command == "start":
            hamster_client._activities(" ".join(args[1:]))
        elif assist_command == "export":
            formats = "html tsv xml ical hamster external".split()
            chosen = sys.argv[-1]
            formats = [f for f in formats if not chosen or f.startswith(chosen)]
            print("\n".join(formats))


    def toggle(self):
        self.storage.toggle()


    def start(self, *args):
        '''Start a new activity.'''
        if not args:
            print("Error: please specify activity")
            return 0

        fact = Fact.parse(" ".join(args), range_pos="tail")
        if fact.start_time is None:
            fact.start_time = dt.datetime.now()
        self.storage.check_fact(fact, default_day=dt.hday.today())
        id_ = self.storage.add_fact(fact)
        return id_


    def stop(self, *args):
        '''Stop tracking the current activity.'''
        self.storage.stop_tracking()


    def export(self, *args):
        args = args or []
        export_format, start_time, end_time = "html", None, None
        if args:
            export_format = args[0]
        (start_time, end_time), __ = dt.Range.parse(" ".join(args[1:]))

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
        (start_time, end_time), __ = dt.Range.parse(" ".join(times or []))

        start_time = start_time or dt.datetime.combine(dt.date.today(), dt.time())
        end_time = end_time or start_time.replace(hour=23, minute=59, second=59)
        self._list(start_time, end_time)


    def current(self, *args):
        """prints current activity. kinda minimal right now"""
        facts = self.storage.get_todays_facts()
        if facts and not facts[-1].end_time:
            print("{} {}".format(str(facts[-1]).strip(),
                                 facts[-1].delta.format(fmt="HH:MM")))
        else:
            print((_("No activity")))


    def search(self, *args):
        """search for activities by name and optionally within a date range"""
        args = args or []
        search = ""
        if args:
            search = args[0]

        (start_time, end_time), __ = dt.Range.parse(" ".join(args[1:]))

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
            cats.append("{}: {}".format(cat, duration.format()))
            total_duration += duration

        for line in word_wrap(", ".join(cats), 80):
            print(line)
        print("Total: ", total_duration.format())

        print()


    def version(self):
        print(hamster.__version__)


if __name__ == '__main__':
    from hamster.lib import i18n
    i18n.setup_i18n()

    usage = _(
"""
Actions:
    * add [activity [start-time [end-time]]]: Add an activity
    * stop: Stop tracking current activity.
    * list [start-date [end-date]]: List activities
    * search [terms] [start-date [end-date]]: List activities matching a search
      term
    * export [html|tsv|ical|xml|hamster|external] [start-date [end-date]]: Export activities with
      the specified format
    * current: Print current activity
    * activities: List all the activities names, one per line.
    * categories: List all the categories names, one per line.

    * overview / preferences / add / about: launch specific window

    * version: Show the Hamster version

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

    hamster_client = HamsterCli()
    app = Hamster()
    logger.debug("app instanciated")

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

    args, unknown_args = parser.parse_known_args()

    # logger for current script
    logger.setLevel(args.log_level)
    # hamster_logger for the rest
    hamster_logger.setLevel(args.log_level)

    if not hamster.installed:
        logger.info("Running in devel mode")

    if args.action in ("start", "track"):
        action = "add"  # alias
    elif args.action == "prefs":
        # for backward compatibility
        action = "preferences"
    else:
        action = args.action

    if action in ("about", "add", "edit", "overview", "preferences"):
        if action == "add" and args.action_args:
            assert not unknown_args, "unknown options: {}".format(unknown_args)
            # directly add fact from arguments
            id_ = hamster_client.start(*args.action_args)
            assert id_ > 0, "failed to add fact"
            sys.exit(0)
        else:
            app.register()
            if action == "edit":
                assert len(args.action_args) == 1, (
                       "edit requires exactly one argument, got {}"
                       .format(args.action_args))
                id_ = int(args.action_args[0])
                assert id_ > 0, "received non-positive id : {}".format(id_)
                action_data = glib.Variant.new_int32(id_)
            else:
                action_data = None
            app.activate_action(action, action_data)
            run_args = [sys.argv[0]] + unknown_args
            logger.debug("run {}".format(run_args))
            status = app.run(run_args)
            logger.debug("app exited")
            sys.exit(status)
    elif hasattr(hamster_client, action):
        getattr(hamster_client, action)(*args.action_args)
    else:
        sys.exit(usage % {'prog': sys.argv[0]})
