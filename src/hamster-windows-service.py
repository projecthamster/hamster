#!/usr/bin/env python3
# nicked off hamster-service

import dbus
import dbus.service
import subprocess

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib as glib

DBusGMainLoop(set_as_default=True)
loop = glib.MainLoop()

if "org.gnome.Hamster.WindowServer" in dbus.SessionBus().list_names():
    print("Found hamster-window-service already running, exiting")
    quit()


# Legacy server. Still used by the shell-extension.
# new code could access the org.gnome.Hamster.GUI actions directly
# http://lazka.github.io/pgi-docs/Gio-2.0/classes/Application.html#Gio.Application
# > The actions are also exported on the session bus,
#   and GIO provides the Gio.DBusActionGroup wrapper
#   to conveniently access them remotely.
class WindowServer(dbus.service.Object):
    __dbus_object_path__ = "/org/gnome/Hamster/WindowServer"

    def __init__(self, loop):
        self.app = True
        self.mainloop = loop
        self.bus = dbus.SessionBus()
        bus_name = dbus.service.BusName("org.gnome.Hamster.WindowServer", bus=self.bus)
        dbus.service.Object.__init__(self, bus_name, self.__dbus_object_path__)

    @dbus.service.method("org.gnome.Hamster")
    def Quit(self):
        """Shutdown the service"""
        self.mainloop.quit()

    def _open_window(self, name):
        subprocess.run("hamster {} &".format(name),
                       shell=True)

    @dbus.service.method("org.gnome.Hamster.WindowServer")
    def edit(self, id=None):
        if id:
            # Need an edit <id> command in cli
            raise NotImplementedError()
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

    from hamster.lib.configuration import runtime, dialogs, conf, load_ui_file
    window_server = WindowServer(loop)

    print("hamster-window-service up")

    loop.run()
