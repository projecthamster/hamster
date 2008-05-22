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


PROFILE = False
if PROFILE:
    import statprof
    statprof.start()

import gtk, gnomeapplet
import getopt, sys
from os.path import *
import gettext, locale

# Allow to use uninstalled
def _check(path):
    return exists(path) and isdir(path) and isfile(path+"/AUTHORS")

name = join(dirname(__file__), '..')
if _check(name):
    print 'Running uninstalled hamster, modifying PYTHONPATH'
    sys.path.insert(0, abspath(name))
else:
    sys.path.insert(0, abspath("@PYTHONDIR@"))
    print "Running installed hamster, using [@PYTHONDIR@:$PYTHONPATH]"

# Now the path is set, import our applet
import hamster.defs

# Setup i18n
gettext.bindtextdomain('hamster-applet', abspath(join(hamster.defs.DATA_DIR, "locale")))
if hasattr(gettext, 'bind_textdomain_codeset'):
    gettext.bind_textdomain_codeset('hamster-applet','UTF-8')
gettext.textdomain('hamster-applet')

locale.bindtextdomain('hamster-applet', abspath(join(hamster.defs.DATA_DIR, "locale")))
if hasattr(locale, 'bind_textdomain_codeset'):
    locale.bind_textdomain_codeset('hamster-applet','UTF-8')
locale.textdomain('hamster-applet')

hamster.__init_db()
import hamster.applet

def applet_factory(applet, iid):
    print 'Starting Hamster instance:', applet, iid
    hamster.applet.HamsterApplet(applet)
    return True

# Return a standalone window that holds the applet
def build_window():
    app = gtk.Window(gtk.WINDOW_TOPLEVEL)
    app.set_title(_(u"Hamster Applet"))
    app.connect("destroy", on_destroy)

    applet = gnomeapplet.Applet()
    applet.get_orient = lambda: gnomeapplet.ORIENT_DOWN
    applet_factory(applet, None)
    applet.reparent(app)

    app.show_all()

    return app

def on_destroy(event):
    from hamster.Configuration import GconfStore
    config = GconfStore.get_instance()
    
    # handle config option to stop tracking on shutdown
    if config.get_stop_on_shutdown():
        from hamster import storage
        last_activity = storage.get_last_activity()
        if last_activity['end_time'] == None:
            storage.touch_fact(last_activity)
        
    gtk.main_quit()

def usage():
    print _(u"""=== Hamster applet: Usage
$ hamster-applet [OPTIONS]

OPTIONS:
    -w, --window    Launch the applet in a standalone window for test purposes (default=no).
    -t, --trace        Use tracing (default=no).
    """)
    sys.exit()

if __name__ == "__main__":
    standalone = False
    do_trace = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "wt", ["window", "trace"])
    except getopt.GetoptError:
        # Unknown args were passed, we fallback to bahave as if
        # no options were passed
        print "WARNING: Unknown arguments passed, using defaults."
        opts = []
        args = sys.argv[1:]

    for o, a in opts:
        if o in ("-w", "--window"):
            standalone = True
        elif o in ("-t", "--trace"):
            do_trace = True

    print 'Running with options:', {
        'standalone': standalone,
        'do_trace': do_trace,
    }

    if standalone:
        import gnome
        gnome.init(hamster.defs.PACKAGE, hamster.defs.VERSION)
        build_window()

        # run the new command using the given trace
        if do_trace:
            import trace
            trace = trace.Trace(
                ignoredirs=[sys.prefix],
                ignoremods=['sys', 'os', 'getopt'],
                trace=True,
                count=False)
            trace.run('gtk.main()')
        else:
            gtk.main()

    else:
        gnomeapplet.bonobo_factory(
            "OAFIID:Hamster_Applet_Factory",
            gnomeapplet.Applet.__gtype__,
            hamster.defs.PACKAGE,
            hamster.defs.VERSION,
            applet_factory)

    if PROFILE:
        statprof.stop()
        statprof.display()

