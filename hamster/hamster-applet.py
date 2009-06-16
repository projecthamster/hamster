#!/usr/bin/env python
# - coding: utf-8 -

# Copyright (C) 2007, 2008 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>

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

import gtk, gnomeapplet
import getopt, sys
import os.path
import gettext, locale
import gnome

# check from AUTHORS file and if one found - we are running from sources
name = os.path.join(os.path.dirname(__file__), '..')
if os.path.exists(os.path.join(name, 'AUTHORS')):
    print 'Running from source folder, modifying PYTHONPATH'
    sys.path.insert(0, os.path.join(name, "hamster", "keybinder", ".libs"))
    sys.path.insert(0, name)

# Now the path is set, import our applet
import hamster
from hamster import defs

# Setup i18n
locale_dir = os.path.abspath(os.path.join(defs.DATA_DIR, "locale"))

for module in (gettext, locale):
    module.bindtextdomain('hamster-applet', locale_dir)
    module.textdomain('hamster-applet')

    if hasattr(module, 'bind_textdomain_codeset'):
        module.bind_textdomain_codeset('hamster-applet','UTF-8')


hamster.__init_db()
from hamster.applet import HamsterApplet

def applet_factory(applet, iid):
    applet.connect("destroy", on_destroy)
    applet.set_applet_flags(gnomeapplet.EXPAND_MINOR)

    hamster_applet = HamsterApplet(applet)

    applet.setup_menu_from_file(hamster.SHARED_DATA_DIR, "Hamster_Applet.xml",
                    None, [("about", hamster_applet.on_about),
                           ("overview", hamster_applet.show_overview),
                           ("preferences", hamster_applet.show_preferences)])

    applet.show_all()
    applet.set_background_widget(applet)

    return True

def on_destroy(event):
    from hamster.configuration import GconfStore
    config = GconfStore.get_instance()
    
    # handle config option to stop tracking on shutdown
    if config.get_stop_on_shutdown():
        from hamster import storage
        last_activity = storage.get_last_activity()
        if last_activity and last_activity['end_time'] is None:
            storage.touch_fact(last_activity)
        
    if gtk.main_level():
        gtk.main_quit()

def usage():
    print _(u"""Time tracker: Usage
$ hamster-applet [OPTIONS]

OPTIONS:
    -w, --window    Launch the applet in a standalone window for test purposes
                    (default=no).
    -s, --start     [stats|edit|prefs] Which window to launch on startup.
                    Use "stats" for overview window, "edit" to add new activity
                    and "prefs" to launch preferences
    -t  --trace-sql print out sql statements in terminal
    """)

if __name__ == "__main__":
    standalone = False
    start_window = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "ws:t", ["window", "start=", "trace-sql"])

        for opt, args in opts:
            if opt in ("-w", "--window"):
                standalone = True
            elif opt in ("-s", "--start"):
                start_window = args
            elif opt in ("-t", "--trace-sql"):
                hamster.trace_sql = True
                
            
    except getopt.GetoptError:
        usage()
        print "Starting nevertheless, because applet dies otherwise (TODO)"


    gtk.window_set_default_icon_name("hamster-applet")

    if standalone:
        gnome.init(defs.PACKAGE, defs.VERSION)

        app = gtk.Window(gtk.WINDOW_TOPLEVEL)
        app.set_title(_(u"Time Tracker"))
    
        applet = gnomeapplet.Applet()
        applet_factory(applet, None)
        applet.reparent(app)
        app.show_all()

        gtk.main()

    elif start_window:
        if start_window == "stats":
            from hamster.stats import StatsViewer
            stats_viewer = StatsViewer().show()
        elif start_window == "edit":
            from hamster.edit_activity import CustomFactController
            CustomFactController().show()
        elif start_window == "prefs":
            from hamster.preferences import PreferencesEditor
            PreferencesEditor().show()
            
        gtk.main()

    else:
        gnomeapplet.bonobo_factory(
            "OAFIID:Hamster_Applet_Factory",
            gnomeapplet.Applet.__gtype__,
            defs.PACKAGE,
            defs.VERSION,
            applet_factory)
