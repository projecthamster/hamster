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
from hamster import dispatcher

class GconfStore(object):
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
        
    @staticmethod
    def get_instance():
        if not GconfStore.__instance:
            GconfStore.__instance = GconfStore()
        return GconfStore.__instance
        
    def __init__(self):
        """
        Do not use the constructor directly. Always use L{get_instance}
        Because otherwise you will have lots of signals running arround
        """
        super(GconfStore, self).__init__()
        self._client = gconf.client_get_default()
        self.__connect_notifications()
        
    def __connect_notifications(self):
        self._client.add_dir(self.GCONF_DIR, gconf.CLIENT_PRELOAD_RECURSIVE)
        self._client.notify_add(self.GCONF_KEYBINDING, lambda x, y, z, a: dispatcher.dispatch("gconf_keybinding_changed", z.value.get_string()))
        self._client.notify_add(self.GCONF_ENABLE_TIMEOUT, lambda x, y, z, a: dispatcher.dispatch("gconf_timeout_enabled_changed", z.value.get_bool()))
        self._client.notify_add(self.GCONF_STOP_ON_SHUTDOWN, lambda x, y, z, a: dispatcher.dispatch("gconf_stop_on_shutdown_changed", z.value.get_bool()))
        self._client.notify_add(self.GCONF_NOTIFY_INTERVAL, lambda x, y, z, a: dispatcher.dispatch("gconf_notify_interval_changed", z.value.get_int()))
        self._client.notify_add(self.GCONF_NOTIFY_ON_IDLE, lambda x, y, z, a: dispatcher.dispatch("gconf_notify_on_idle_changed", z.value.get_bool()))

    
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
        
