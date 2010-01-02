# -*- coding: utf-8 -*-

# Copyright (C) 2008 Toms Bauģis <toms.baugis at gmail.com>

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

import gconf
import gettext
import os
import defs
from db import Storage
from dispatcher import Dispatcher
from xdg.BaseDirectory import xdg_data_home
import logging
import datetime as dt
import gio

class Singleton(object):
     def __new__(cls, *args, **kwargs):
         if '__instance' not in vars(cls):
             cls.__instance = object.__new__(cls, *args, **kwargs)
         return cls.__instance

class RuntimeStore(Singleton):
    """
    Handles one-shot configuration that is not stored between sessions
    """
    database_path = ""
    database_file = None
    last_etag = None
    data_dir = ""
    dispatcher = None
    storage = None
    

    def __init__(self):
        gettext.install("hamster-applet", unicode = True)

        # Typically shared data dir is /usr/share/hamster-applet
        if os.path.realpath(__file__).startswith(defs.PYTHONDIR):
            data_dir = os.path.join(defs.DATA_DIR, "hamster-applet")
        else:
            data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.data_dir = data_dir
        self.dispatcher = Dispatcher()
        self.storage = Storage(self.dispatcher)

        # figure out the correct database file
        old_db_file = os.path.expanduser("~/.gnome2/hamster-applet/hamster.db")
        new_db_file = os.path.join(xdg_data_home, "hamster-applet", "hamster.db")
        
        if os.path.exists(old_db_file):
            db_path, _ = os.path.split(os.path.realpath(new_db_file))
            if not os.path.exists(db_path):
                try:
                    os.makedirs(db_path, 0744)
                except Exception, msg:
                    logging.error("could not create user dir (%s): %s" % (db_path, msg))
            if os.path.exists(new_db_file):
                logging.info("Have two database %s and %s" % (new_db_file, old_db_file))
            else:
                os.rename(old_db_file, new_db_file)
        
        self.database_path = new_db_file


        # add file monitoring so the app does not have to be restarted
        # when db file is rewritten
        def on_db_file_change(monitor, gio_file, event_uri, event):
            if event == gio.FILE_MONITOR_EVENT_CHANGES_DONE_HINT:
                if gio_file.query_info(gio.FILE_ATTRIBUTE_ETAG_VALUE).get_etag() == self.last_etag:
                    # ours
                    return
                
                logging.info("DB file has been modified externally. Calling all stations")
                self.storage.dispatch_overwrite()


        
        self.database_file = gio.File(self.database_path)
        self.db_monitor = self.database_file.monitor_file()
        self.db_monitor.connect("changed", on_db_file_change)


    def register_modification(self):
        # db.execute calls this so we know that we were the ones
        # that modified the DB and no extra refesh is not needed
        self.last_etag = self.database_file.query_info(gio.FILE_ATTRIBUTE_ETAG_VALUE).get_etag()


    @property
    def art_dir(self):
        return os.path.join(self.data_dir, "art")


runtime = RuntimeStore()


class OneWindow(object):
    def __init__(self, get_dialog_class):
        self.dialogs = {}
        self.get_dialog_class = get_dialog_class
    
    def on_dialog_destroy(self, params):
        del self.dialogs[params]
        #self.dialogs[params] = None

    def show(self, parent = None, **kwargs):
        params = str(sorted(kwargs.items())) #this is not too safe but will work for most cases
        
        if params in self.dialogs:
            self.dialogs[params].window.present()
        else:
            if parent:
                dialog = self.get_dialog_class()(parent, **kwargs)
                dialog.window.set_transient_for(parent.get_toplevel())
            else:
                dialog = self.get_dialog_class()(**kwargs)
            
            # to make things simple, we hope that the target has defined self.window
            dialog.window.connect("destroy",
                                  lambda window, params: self.on_dialog_destroy(params),
                                  params)
            
            self.dialogs[params] = dialog

class Dialogs(Singleton):
    """makes sure that we have single instance open for windows where it makes
       sense"""
    def __init__(self):
        def get_edit_class():
            from edit_activity import CustomFactController
            return CustomFactController
        self.edit = OneWindow(get_edit_class)

        def get_overview_class():
            from stats import StatsViewer
            return StatsViewer
        self.overview = OneWindow(get_overview_class)

        def get_stats_class():
            from stats_stats import StatsViewer
            return StatsViewer
        self.stats = OneWindow(get_stats_class)

        def get_about_class():
            from about import About
            return About
        self.about = OneWindow(get_about_class)

        def get_prefs_class():
            from preferences import PreferencesEditor
            return PreferencesEditor
        self.prefs = OneWindow(get_prefs_class)

dialogs = Dialogs()    

class GconfStore(Singleton):
    """
    Handles storing to and retrieving values from GConf 
    """

    # GConf directory for deskbar in window mode and shared settings
    GCONF_DIR = "/apps/hamster-applet/general"
    
    # GConf key for global keybinding
    GCONF_KEYBINDING = GCONF_DIR + "/keybinding"
    GCONF_ENABLE_TIMEOUT = GCONF_DIR + "/enable_timeout"
    GCONF_STOP_ON_SHUTDOWN = GCONF_DIR + "/stop_on_shutdown"  
    GCONF_NOTIFY_INTERVAL = GCONF_DIR + "/notify_interval" 
    GCONF_NOTIFY_ON_IDLE = GCONF_DIR + "/notify_on_idle"
    GCONF_DAY_START = GCONF_DIR + "/day_start"

    __instance = None
        
    def __init__(self):
        super(GconfStore, self).__init__()
        self._client = gconf.client_get_default()
        self.__connect_notifications()
        
    def __connect_notifications(self):
        self._client.add_dir(self.GCONF_DIR, gconf.CLIENT_PRELOAD_RECURSIVE)
        self._client.notify_add(self.GCONF_KEYBINDING, lambda x, y, z, a: runtime.dispatcher.dispatch("gconf_keybinding_changed", z.value.get_string()))
        self._client.notify_add(self.GCONF_ENABLE_TIMEOUT, lambda x, y, z, a: runtime.dispatcher.dispatch("gconf_timeout_enabled_changed", z.value.get_bool()))
        self._client.notify_add(self.GCONF_STOP_ON_SHUTDOWN, lambda x, y, z, a: runtime.dispatcher.dispatch("gconf_stop_on_shutdown_changed", z.value.get_bool()))
        self._client.notify_add(self.GCONF_NOTIFY_INTERVAL, lambda x, y, z, a: runtime.dispatcher.dispatch("gconf_notify_interval_changed", z.value.get_int()))
        self._client.notify_add(self.GCONF_NOTIFY_ON_IDLE, lambda x, y, z, a: runtime.dispatcher.dispatch("gconf_notify_on_idle_changed", z.value.get_bool()))
        self._client.notify_add(self.GCONF_DAY_START, lambda x, y, z, a: runtime.dispatcher.dispatch("gconf_on_day_start_changed", z.value.get_int()))

    
    def get_keybinding(self):
        return self._client.get_string(self.GCONF_KEYBINDING) or ""
    
    def get_timeout_enabled(self):
        return self._client.get_bool(self.GCONF_ENABLE_TIMEOUT) or False

    def get_stop_on_shutdown(self):
        return self._client.get_bool(self.GCONF_STOP_ON_SHUTDOWN) or False
        
    def get_notify_interval(self):
    	return self._client.get_int(self.GCONF_NOTIFY_INTERVAL) or 27

    def get_notify_on_idle(self):
    	return self._client.get_bool(self.GCONF_NOTIFY_ON_IDLE) or False

    def get_day_start(self):
        minutes = self._client.get_int(self.GCONF_DAY_START) or 5*60 + 30
        return dt.time(minutes / 60, minutes % 60)

    #------------------------    
    def set_keybinding(self, binding):
        self._client.set_string(self.GCONF_KEYBINDING, binding)
    
    def set_timeout_enabled(self, enabled):
        self._client.set_bool(self.GCONF_ENABLE_TIMEOUT, enabled)
        
    def set_stop_on_shutdown(self, enabled):
        self._client.set_bool(self.GCONF_STOP_ON_SHUTDOWN, enabled)
    
    def set_notify_interval(self, interval):
    	return self._client.set_int(self.GCONF_NOTIFY_INTERVAL, interval)

    def set_notify_on_idle(self, enabled):
        self._client.set_bool(self.GCONF_NOTIFY_ON_IDLE, enabled)

    def set_day_start(self, time):
    	return self._client.set_int(self.GCONF_DAY_START, time.hour * 60 + time.minute)

