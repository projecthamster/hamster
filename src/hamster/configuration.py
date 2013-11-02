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

"""
gconf part of this code copied from Gimmie (c) Alex Gravely via Conduit (c) John Stowers, 2006
License: GPLv2
"""

import gconf
import os
from client import Storage
from xdg.BaseDirectory import xdg_data_home
import logging
import datetime as dt
import gobject, gtk

import logging
log = logging.getLogger("configuration")

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
    home_data_dir = ""
    storage = None
    conf = None


    def __init__(self):
        try:
            import defs
            self.data_dir = os.path.join(defs.DATA_DIR, "hamster-time-tracker")
            self.version = defs.VERSION
        except:
            # if defs is not there, we are running from sources
            module_dir = os.path.dirname(os.path.realpath(__file__))
            self.data_dir = os.path.join(module_dir, '..', '..', 'data')
            self.version = "uninstalled"

        self.data_dir = os.path.realpath(self.data_dir)


        self.storage = Storage()


        self.home_data_dir = os.path.realpath(os.path.join(xdg_data_home, "hamster-time-tracker"))

    @property
    def art_dir(self):
        return os.path.join(self.data_dir, "art")


runtime = RuntimeStore()


class OneWindow(object):
    def __init__(self, get_dialog_class):
        self.dialogs = {}
        self.get_dialog_class = get_dialog_class
        self.dialog_close_handlers = {}

    def on_close_window(self, dialog):
        for key, assoc_dialog in list(self.dialogs.iteritems()):
            if dialog == assoc_dialog:
                del self.dialogs[key]

        handler = self.dialog_close_handlers.pop(dialog)
        dialog.disconnect(handler)


    def show(self, parent = None, **kwargs):
        params = str(sorted(kwargs.items())) #this is not too safe but will work for most cases

        if params in self.dialogs:
            window = self.dialogs[params].window
            self.dialogs[params].show()
            window.present()
        else:
            if parent:
                dialog = self.get_dialog_class()(parent, **kwargs)

                if isinstance(parent, gtk.Widget):
                    dialog.window.set_transient_for(parent.get_toplevel())

                self.dialog_close_handlers[dialog] = dialog.connect("on-close", self.on_close_window)
            else:
                dialog = self.get_dialog_class()(**kwargs)

                # no parent means we close on window close
                dialog.window.connect("destroy",
                                      lambda window, params: gtk.main_quit(),
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
            from overview import Overview
            return Overview
        self.overview = OneWindow(get_overview_class)

        def get_stats_class():
            from stats import Stats
            return Stats
        self.stats = OneWindow(get_stats_class)

        def get_about_class():
            from about import About
            return About
        self.about = OneWindow(get_about_class)

        def get_prefs_class():
            from preferences import PreferencesEditor
            return PreferencesEditor
        self.prefs = OneWindow(get_prefs_class)

        def get_export_rt_class():
            from exportrt import ExportRtController
            return ExportRtController
        self.export_rt = OneWindow(get_export_rt_class)

dialogs = Dialogs()


def load_ui_file(name):
    ui = gtk.Builder()
    ui.add_from_file(os.path.join(runtime.data_dir, name))
    return ui

class GConfStore(gobject.GObject, Singleton):
    """
    Settings implementation which stores settings in GConf
    Snatched from the conduit project (http://live.gnome.org/Conduit)
    """
    GCONF_DIR = "/apps/hamster-time-tracker/"
    VALID_KEY_TYPES = (bool, str, int, list, tuple)
    DEFAULTS = {
        'enable_timeout'              :   False,       # Should hamster stop tracking on idle
        'stop_on_shutdown'            :   False,       # Should hamster stop tracking on shutdown
        'notify_on_idle'              :   False,       # Remind also if no activity is set
        'notify_interval'             :   27,          # Remind of current activity every X minutes
        'day_start_minutes'           :   5 * 60 + 30, # At what time does the day start (5:30AM)
        'overview_window_box'         :   [],          # X, Y, W, H
        'overview_window_maximized'   :   False,       # Is overview window maximized
        'workspace_tracking'          :   [],          # Should hamster switch activities on workspace change 0,1,2
        'workspace_mapping'           :   [],          # Mapping between workspace numbers and activities
        'standalone_window_box'       :   [],          # X, Y, W, H
        'standalone_window_maximized' :   False,       # Is overview window maximized
        'activities_source'           :   "",          # Source of TODO items ("", "evo", "gtg")
        'last_report_folder'          :   "~",         # Path to directory where the last report was saved
        'icon_glow'                   :   True,
        'show_label'                  :   False,
        'label_length'                :   20,
        'last_activities_days'        :   7,
        'rt_url'                      :   "https://rt.contium.pl/REST/1.0/",          # RT REST url
        'rt_user'                     :   "",          # 
        'rt_pass'                     :   "",          # 
        'rt_query'                    :   "Owner='__CurrentUser__' AND (Status='new' OR Status='open')",          # RT query for autocomplete
        'rt_category_field'           :   "CF.{Projekt}",
        'rt_activities_only'          :   True,
    }

    __gsignals__ = {
        "conf-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))
    }
    def __init__(self):
        gobject.GObject.__init__(self)
        self._client = gconf.client_get_default()
        self._client.add_dir(self.GCONF_DIR[:-1], gconf.CLIENT_PRELOAD_RECURSIVE)
        self._notifications = []

    def _fix_key(self, key):
        """
        Appends the GCONF_PREFIX to the key if needed

        @param key: The key to check
        @type key: C{string}
        @returns: The fixed key
        @rtype: C{string}
        """
        if not key.startswith(self.GCONF_DIR):
            return self.GCONF_DIR + key
        else:
            return key

    def _key_changed(self, client, cnxn_id, entry, data=None):
        """
        Callback when a gconf key changes
        """
        key = self._fix_key(entry.key)[len(self.GCONF_DIR):]
        value = self._get_value(entry.value, self.DEFAULTS[key])

        self.emit('conf-changed', key, value)


    def _get_value(self, value, default):
        """calls appropriate gconf function by the default value"""
        vtype = type(default)

        if vtype is bool:
            return value.get_bool()
        elif vtype is str:
            return value.get_string()
        elif vtype is int:
            return value.get_int()
        elif vtype in (list, tuple):
            l = []
            for i in value.get_list():
                l.append(i.get_string())
            return l

        return None

    def get(self, key, default=None):
        """
        Returns the value of the key or the default value if the key is
        not yet in gconf
        """

        #function arguments override defaults
        if default is None:
            default = self.DEFAULTS.get(key, None)
        vtype = type(default)

        #we now have a valid key and type
        if default is None:
            log.warn("Unknown key: %s, must specify default value" % key)
            return None

        if vtype not in self.VALID_KEY_TYPES:
            log.warn("Invalid key type: %s" % vtype)
            return None

        #for gconf refer to the full key path
        key = self._fix_key(key)

        if key not in self._notifications:
            self._client.notify_add(key, self._key_changed)
            self._notifications.append(key)

        value = self._client.get(key)
        if value is None:
            self.set(key, default)
            return default

        value = self._get_value(value, default)
        if value is not None:
            return value

        log.warn("Unknown gconf key: %s" % key)
        return None

    def set(self, key, value):
        """
        Sets the key value in gconf and connects adds a signal
        which is fired if the key changes
        """
        log.debug("Settings %s -> %s" % (key, value))
        if key in self.DEFAULTS:
            vtype = type(self.DEFAULTS[key])
        else:
            vtype = type(value)

        if vtype not in self.VALID_KEY_TYPES:
            log.warn("Invalid key type: %s" % vtype)
            return False

        #for gconf refer to the full key path
        key = self._fix_key(key)

        if vtype is bool:
            self._client.set_bool(key, value)
        elif vtype is str:
            self._client.set_string(key, value)
        elif vtype is int:
            self._client.set_int(key, value)
        elif vtype in (list, tuple):
            #Save every value as a string
            strvalues = [str(i) for i in value]
            self._client.set_list(key, gconf.VALUE_STRING, strvalues)

        return True


conf = GConfStore()
