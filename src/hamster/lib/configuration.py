# -*- coding: utf-8 -*-

# Copyright (C) 2008, 2014 Toms Bauģis <toms.baugis at gmail.com>

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


import logging
logger = logging.getLogger(__name__)   # noqa: E402

import os
import json
import datetime as dt
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from xdg.BaseDirectory import xdg_data_home, xdg_config_home
from hamster.client import Storage


class Controller(gobject.GObject):
    __gsignals__ = {
        "on-close": (gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, parent=None, ui_file=""):
        gobject.GObject.__init__(self)

        self.parent = parent

        if ui_file:
            self._gui = load_ui_file(ui_file)
            self.window = self.get_widget('window')
        else:
            self._gui = None
            self.window = gtk.Window()

        self.window.connect("delete-event", self.window_delete_event)
        if self._gui:
            self._gui.connect_signals(self)


    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)


    def window_delete_event(self, widget, event):
        self.close_window()

    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            """
            for obj, handler in self.external_listeners:
                obj.disconnect(handler)
            """
            self.window.destroy()
            self.window = None
            self.emit("on-close")

    def show(self):
        self.window.show()


def load_ui_file(name):
    """loads interface from the glade file; sorts out the path business"""
    ui = gtk.Builder()
    ui.add_from_file(os.path.join(runtime.data_dir, name))
    return ui



class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if '__instance' not in vars(cls):
            cls.__instance = object.__new__(cls, *args, **kwargs)
        return cls.__instance

class RuntimeStore(Singleton):
    """XXX - kill"""
    data_dir = ""
    home_data_dir = ""
    storage = None

    def __init__(self):
        try:
            from hamster import defs
            self.data_dir = os.path.join(defs.DATA_DIR, "hamster-time-tracker")
            self.version = defs.VERSION
        except:
            # if defs is not there, we are running from sources
            module_dir = os.path.dirname(os.path.realpath(__file__))
            self.data_dir = os.path.join(module_dir, '..', '..', '..', 'data')
            self.version = "uninstalled"

        self.data_dir = os.path.realpath(self.data_dir)
        self.storage = Storage()
        self.home_data_dir = os.path.realpath(os.path.join(xdg_data_home, "hamster-time-tracker"))


runtime = RuntimeStore()


class OneWindow(object):
    def __init__(self, get_dialog_class):
        self.dialogs = {}
        self.get_dialog_class = get_dialog_class
        self.dialog_close_handlers = {}

    def on_close_window(self, dialog):
        for key, assoc_dialog in list(self.dialogs.items()):
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

                if hasattr(dialog, "connect"):
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
            from hamster.edit_activity import CustomFactController
            return CustomFactController
        self.edit = OneWindow(get_edit_class)

        def get_overview_class():
            from hamster.overview import Overview
            return Overview
        self.overview = OneWindow(get_overview_class)

        def get_about_class():
            from hamster.about import About
            return About
        self.about = OneWindow(get_about_class)

        def get_prefs_class():
            from hamster.preferences import PreferencesEditor
            return PreferencesEditor
        self.prefs = OneWindow(get_prefs_class)

dialogs = Dialogs()


class ConfStore(Singleton):
    """
    Settings implementation which stores settings as json string in hamster.db
    """
    DEFAULTS = {
        'enable_timeout'              :   False,       # Should hamster stop tracking on idle
        'stop_on_shutdown'            :   False,       # Should hamster stop tracking on shutdown
        'notify_on_idle'              :   False,       # Remind also if no activity is set
        'notify_interval'             :   27,          # Remind of current activity every X minutes
        'day_start_minutes'           :   5 * 60 + 30, # At what time does the day start (5:30AM)
        'activities_source'           :   "",          # Source of TODO items ("", "evo", "gtg")
        'last_report_folder'          :   "~",         # Path to directory where the last report was saved
    }
    #    'workspace_tracking           :   []           # ???
    #    'workspace_mapping            :   []           # ???
    #    'overview_window_box'         :   [],          # X, Y, W, H
    #    'overview_window_maximized'   :   False,       # Is overview window maximized
    #    'standalone_window_box'       :   [],          # X, Y, W, H
    #    'standalone_window_maximized' :   False,       # Is overview window maximized

    def __init__(self):
        self.config = self.DEFAULTS
        config_dir = os.path.join(xdg_config_home, 'hamster-time-tracker')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        self.config_file = os.path.join(config_dir, 'hamster.json')
        if os.path.exists(self.config_file):
            self._load_config()
        else:
            self._save_config()

    def _save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, sort_keys=True, indent=4)

    def _load_config(self):
        with open(self.config_file, 'r') as f:
            self.config.update(json.load(f))

    def get(self, key):
        """
        Returns the value of the conf key
        """
        # for now, update from config file every time (ugh)
        # - later update config only on external file change
        self._load_config()

        if key not in self.config:
            logger.warn("Unknown config key: %s" % key)
            return None
        else:
            return self.config[key]

    def set(self, key, value):
        """
        Set the key value and save config file
        """
        logger.info("Settings %s -> %s" % (key, value))

        self.config[key] = value
        self._save_config()

        return True

    @property
    def day_start(self):
        """Start of the hamster day."""
        day_start_minutes = self.config["day_start_minutes"]
        hours, minutes = divmod(day_start_minutes, 60)
        return dt.time(hours, minutes)


conf = ConfStore()
