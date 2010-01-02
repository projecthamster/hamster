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
import sys
from optparse import OptionParser
import os.path
import gettext, locale
import gnome
import logging
import gobject

def applet_factory(applet, iid):
    applet.connect("destroy", on_destroy)
    applet.set_applet_flags(gnomeapplet.EXPAND_MINOR)

    from hamster.applet import HamsterApplet    
    hamster_applet = HamsterApplet(applet)

    applet.show_all()
    applet.set_background_widget(applet)

    return True

def on_destroy(event):
    from hamster.configuration import GconfStore, runtime
    config = GconfStore()
    
    # handle config option to stop tracking on shutdown
    if config.get_stop_on_shutdown():
        last_activity = runtime.storage.get_last_activity()
        if last_activity and last_activity['end_time'] is None:
            runtime.storage.touch_fact(last_activity)
        
    if gtk.main_level():
        gtk.main_quit()

if __name__ == "__main__":
    parser = OptionParser(usage = "hamster-applet [OPTIONS]")
    parser.add_option("-w", "--window",
                      action="store_true",
                      dest="standalone",
                      default=False,
                      help="Launch the applet in a standalone window")
    parser.add_option("-s",
                      "--start",
                      dest="start_window",
                      help="[stats|edit|prefs] Which window to launch on startup.")
    parser.add_option("-d", "--debug",
                      action="store_true",
                      dest="debug",
                      default=False,
                      help="set log level to debug")
    
    #these two come from bonobo
    parser.add_option("--oaf-activate-iid")
    parser.add_option("--oaf-ior-fd")

    (options, args) = parser.parse_args()

    # in console set logging lower, in panel write log to file
    log_format = "%(asctime)s %(levelname)s: %(message)s"
    if options.standalone or options.start_window:
        log_level = logging.INFO
        if options.debug:
            log_level = logging.DEBUG

        logging.basicConfig(level = log_level, format = log_format)
    else: #otherwise write to the sessions file
        logging.basicConfig(filename = os.path.join(os.path.expanduser("~"),
                                                    '.xsession-errors'),
                            format = log_format)

    try:
        # by AUTHORS file determine if we run from sources or installed
        name = os.path.join(os.path.dirname(__file__), '..')
        if os.path.exists(os.path.join(name, 'AUTHORS')):
            logging.info("Running from source folder, modifying PYTHONPATH")
            sys.path.insert(0, os.path.join(name, "hamster", "keybinder", ".libs"))
            sys.path.insert(0, name)
        
        # Now the path is set, import our applet
        from hamster import defs
        from hamster.configuration import runtime, dialogs
        
        # Setup i18n
        locale_dir = os.path.abspath(os.path.join(defs.DATA_DIR, "locale"))        
        for module in (gettext, locale):
            module.bindtextdomain('hamster-applet', locale_dir)
            module.textdomain('hamster-applet')
        
            if hasattr(module, 'bind_textdomain_codeset'):
                module.bind_textdomain_codeset('hamster-applet','UTF-8')
        
        gtk.window_set_default_icon_name("hamster-applet")
    
        if options.start_window or options.standalone:
            gobject.set_application_name("hamster-applet")
            if options.start_window.startswith("over"):
                dialogs.overview.show()

            elif options.start_window == "stats":
                dialogs.stats.show()

            elif options.start_window == "edit":
                dialogs.edit.show()

            elif options.start_window == "prefs":
                dialogs.prefs.show()

            else: #default to main applet
                gnome.init(defs.PACKAGE, defs.VERSION)
        
                app = gtk.Window(gtk.WINDOW_TOPLEVEL)
                app.set_title(_(u"Time Tracker"))
            
                applet = gnomeapplet.Applet()
                applet_factory(applet, None)
                applet.reparent(app)
                app.show_all()

            gtk.main()    
        else:
            gnomeapplet.bonobo_factory(
                "OAFIID:Hamster_Applet_Factory",
                gnomeapplet.Applet.__gtype__,
                defs.PACKAGE,
                defs.VERSION,
                applet_factory)
    except:
        # make sure the error appears somewhere
        import traceback
        logging.error(traceback.format_exc())
