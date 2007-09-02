#!/usr/bin/env python
#
# (C) 2007 Toms Baugis
# Licensed under the GNU LGPL v3.
PROFILE = False
if PROFILE:
    import statprof
    statprof.start()

import gtk, gnomeapplet
import getopt, sys
from os.path import *

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
import hamster, hamster.HamsterApplet, hamster.defs

def applet_factory(applet, iid):
    print 'Starting Hamster instance:', applet, iid
    hamster.HamsterApplet.HamsterApplet(applet)
    return True

# Return a standalone window that holds the applet
def build_window():
    app = gtk.Window(gtk.WINDOW_TOPLEVEL)
    app.set_title("Hamster Applet")
    app.connect("destroy", gtk.main_quit)

    applet = gnomeapplet.Applet()
    applet.get_orient = lambda: gnomeapplet.ORIENT_DOWN
    applet_factory(applet, None)
    applet.reparent(app)

    app.show_all()

    return app

def usage():
    print """=== Hamster applet: Usage
$ hamster-applet [OPTIONS]

OPTIONS:
    -w, --window    Launch the applet in a standalone window for test purposes (default=no).
    -t, --trace        Use tracing (default=no).
    """
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

