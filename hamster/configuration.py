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

class Singleton(object):
     def __new__(cls, *args, **kwargs):
         if '__instance' not in vars(cls):
             cls.__instance = object.__new__(cls, *args, **kwargs)
         return cls.__instance

class RuntimeStore(Singleton):
    """
    Handles one-shot configuration that is not stored between sessions
    """
    database_file = ""
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

    def get_art_dir(self):
        return os.path.join(self.data_dir, "art")

    art_dir = property(get_art_dir, None)

runtime = RuntimeStore()
runtime.database_file = os.path.expanduser("~/.gnome2/hamster-applet/hamster.db")

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

