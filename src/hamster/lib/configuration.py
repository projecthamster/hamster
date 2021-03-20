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

"""
License: GPLv2
"""

import logging

from hamster.external.external import ExternalSource

logger = logging.getLogger(__name__)   # noqa: E402

import os
from hamster.client import Storage
from xdg.BaseDirectory import xdg_data_home

from gi.repository import Gdk as gdk
from gi.repository import Gio as gio
from gi.repository import GLib as glib
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk

import hamster

from hamster.lib import datetime as dt


class Controller(gobject.GObject):
    """Window creator and handler."""
    __gsignals__ = {
        "on-close": (gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, ui_file=""):
        gobject.GObject.__init__(self)

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
        # Do not try to just hide;
        # dialogs are populated upon instanciation anyway
        self.window.destroy()
        self.window = None
        self.emit("on-close")

    def present(self):
        """Show window and bring it to the foreground."""
        # workaround https://gitlab.gnome.org/GNOME/gtk/issues/624
        # fixed in gtk-3.24.1 (2018-09-19)
        # self.overview_controller.window.present()
        self.window.present_with_time(glib.get_monotonic_time() / 1000)

    def show(self):
        """Show window.
        It might be obscurd by others though.
        See also: presents
        """
        self.window.show()

    def __bool__(self):
        return True if self.window else False


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
    external = None
    external_need_update = True

    def __init__(self):
        self.version = hamster.__version__
        if hamster.installed:
            from hamster import defs  # only available when running installed
            self.data_dir = os.path.join(defs.DATA_DIR, "hamster")
        else:
            # running from sources
            module_dir = os.path.dirname(os.path.realpath(__file__))
            self.data_dir = os.path.join(module_dir, '..', '..', '..', 'data')

        self.data_dir = os.path.realpath(self.data_dir)
        self.storage = Storage()
        self.home_data_dir = os.path.realpath(os.path.join(xdg_data_home, "hamster"))

    def get_external(self) -> ExternalSource:
        if self.external_need_update:
            self.refresh_external(conf)
        return self.external

    def refresh_external(self, conf):
        self.external = ExternalSource(conf)
        self.external_need_update = False

runtime = RuntimeStore()


class GSettingsStore(gobject.GObject, Singleton):
    """
    Settings implementation which stores settings in GSettings
    Snatched from the conduit project (http://live.gnome.org/Conduit)
    """

    __gsignals__ = {
        "changed": (gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))
    }

    def __init__(self):
        gobject.GObject.__init__(self)
        self._settings = gio.Settings(schema_id='org.gnome.Hamster')

    def _key_changed(self, client, key, data=None):
        """
        Callback when a GSettings key changes
        """
        value = self._settings.get_value(key)
        self.emit('changed', key, value)

    def get(self, key, default=None):
        """
        Returns the value of the key or the default value if the key is
        not yet in GSettings
        """
        value = self._settings.get_value(key)
        if value is None:
            logger.warn("Unknown GSettings key: %s" % key)

        return value.unpack()

    def set(self, key, value):
        """
        Sets the key value in GSettings and connects adds a signal
        which is fired if the key changes
        """
        logger.debug("Settings %s -> %s" % (key, value))
        default = self._settings.get_default_value(key)
        assert default is not None
        self._settings.set_value(key, glib.Variant(default.get_type().dup_string(), value))
        return True

    def bind(self, key, obj, prop):
        self._settings.bind(key, obj, prop, gio.SettingsBindFlags.DEFAULT)

    @property
    def day_start(self):
        """Start of the hamster day."""
        day_start_minutes = self.get("day-start-minutes")
        hours, minutes = divmod(day_start_minutes, 60)
        return dt.time(hours, minutes)


conf = GSettingsStore()
