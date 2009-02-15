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

# Allow to use uninstalled
def _check(path):
    return os.path.exists(path) and os.path.isdir(path) \
           and os.path.isfile(path + "/AUTHORS")

name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _check(name):
    print 'Running uninstalled hamster, modifying PYTHONPATH'
    sys.path.insert(0, os.path.join(name, "hamster", "keybinder/.libs"))
    sys.path.insert(0, name)

# Now the path is set, import our applet
import hamster.defs

# Setup i18n
locale_dir = os.path.abspath(os.path.join(hamster.defs.DATA_DIR, "locale"))

gettext.bindtextdomain('hamster-applet', locale_dir)
if hasattr(gettext, 'bind_textdomain_codeset'):
    gettext.bind_textdomain_codeset('hamster-applet','UTF-8')
gettext.textdomain('hamster-applet')

locale.bindtextdomain('hamster-applet', locale_dir)
if hasattr(locale, 'bind_textdomain_codeset'):
    locale.bind_textdomain_codeset('hamster-applet','UTF-8')
locale.textdomain('hamster-applet')

hamster.__init_db()
import hamster.applet

def applet_factory(applet, iid):
    applet.connect("destroy", on_destroy)
    hamster.applet.HamsterApplet(applet)
    return True

def on_destroy(event):
    from hamster.Configuration import GconfStore
    config = GconfStore.get_instance()
    
    # handle config option to stop tracking on shutdown
    if config.get_stop_on_shutdown():
        from hamster import storage
        last_activity = storage.get_last_activity()
        if last_activity and last_activity['end_time'] == None:
            storage.touch_fact(last_activity)
        
    gtk.main_quit()

def usage():
    print _(u"""=== Time tracking applet: Usage
$ hamster-applet [OPTIONS]

OPTIONS:
    -w, --window    Launch the applet in a standalone window for test purposes (default=no).
    -o, --overview  Launch just the overview window
    """)
    sys.exit()

if __name__ == "__main__":
    standalone = False
    show_overview = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "wo", ["window", "overview"])
    except getopt.GetoptError:
        # Unknown args were passed, we fallback to bahave as if
        # no options were passed
        print "WARNING: Unknown arguments passed, using defaults."
        opts = []
        args = sys.argv[1:]

    for o, a in opts:
        if o in ("-w", "--window"):
            standalone = True
        elif o in ("-o", "--overview"):
            show_overview = True


    gtk.window_set_default_icon_name("hamster-applet")

    if standalone:
        gnome.init(hamster.defs.PACKAGE, hamster.defs.VERSION)

        app = gtk.Window(gtk.WINDOW_TOPLEVEL)
        app.set_title(_(u"Time Tracker"))
    
        applet = gnomeapplet.Applet()
        applet_factory(applet, None)
        applet.reparent(app)
        app.show_all()

        gtk.main()

    elif show_overview:
        from hamster.stats import StatsViewer
        stats_viewer = StatsViewer(True)
        stats_viewer.show()
        gtk.main()

    else:
        gnomeapplet.bonobo_factory(
            "OAFIID:Hamster_Applet_Factory",
            gnomeapplet.Applet.__gtype__,
            hamster.defs.PACKAGE,
            hamster.defs.VERSION,
            applet_factory)
