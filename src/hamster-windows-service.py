#!/usr/bin/env python3
# nicked off hamster-service

import dbus
import dbus.service
import os.path
import subprocess
import sys

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib as glib

import hamster
from hamster.lib import default_logger
from hamster.lib.dbus import claim_bus_name

logger = default_logger(__file__)

DBusGMainLoop(set_as_default=True)
loop = glib.MainLoop()

# Legacy server. Still used by the shell-extension.
# New code _could_ access the org.gnome.Hamster.GUI actions directly,
# although the exact action names/data are subject to change.
# http://lazka.github.io/pgi-docs/Gio-2.0/classes/Application.html#Gio.Application
# > The actions are also exported on the session bus,
#   and GIO provides the Gio.DBusActionGroup wrapper
#   to conveniently access them remotely.
class WindowServer(dbus.service.Object):
    __dbus_object_path__ = "/org/gnome/Hamster/WindowServer"

    def __init__(self, loop, bus, name_obj):
        self.app = True
        self.mainloop = loop
        self.bus = bus
        dbus.service.Object.__init__(self, name_obj, self.__dbus_object_path__)

    @dbus.service.method("org.gnome.Hamster")
    def Quit(self):
        """Shutdown the service"""
        self.mainloop.quit()

    def _open_window(self, name):
        if hamster.installed:
            base_cmd = "hamster"
        else:
            # both scripts are at the same place in the source tree
            cwd = os.path.dirname(__file__)
            base_cmd = "python3 {}/hamster-cli.py".format(cwd)
        cmd = "{} {} &".format(base_cmd, name)
        subprocess.run(cmd, shell=True)

    @dbus.service.method("org.gnome.Hamster.WindowServer")
    def edit(self, id: int = 0):
        """Edit fact, given its id (int) in the database.

        For backward compatibility, if id is 0, create a brand new fact.
        """
        if id:
            # {:d} restrict the string format. Too many safeguards cannot hurt.
            self._open_window("edit {:d}".format(id))
        else:
            self._open_window("add")

    @dbus.service.method("org.gnome.Hamster.WindowServer")
    def overview(self):
        self._open_window("overview")

    @dbus.service.method("org.gnome.Hamster.WindowServer")
    def about(self):
        self._open_window("about")

    @dbus.service.method("org.gnome.Hamster.WindowServer")
    def preferences(self):
        self._open_window("prefs")


if __name__ == '__main__':
    from hamster.lib import i18n
    i18n.setup_i18n()

    glib.set_prgname(str(_("hamster-windows-service")))

    (bus, name_obj) = claim_bus_name("org.gnome.Hamster.WindowServer")
    if name_obj is None:
        logger.error("Found hamster-windows-service already running, exiting")
        sys.exit(1)
    window_server = WindowServer(loop, bus, name_obj)
    logger.info("hamster-window-service up")

    loop.run()
