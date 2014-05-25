# - coding: utf-8 -

# Copyright (C) 2014 Miguel Guedes <miguel.a.guedes@gmail.com>

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

'''Creates a dbus service for the front-end.'''

import dbus, dbus.service

from configuration import dialogs


class FrontendDbusService(dbus.service.Object):
    def __init__(self, app):
        name = dbus.service.BusName('org.gnome.Hamster.Frontend',
                                    bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, name, '/org/gnome/Hamster/Frontend')
        self.app = app

    @dbus.service.method('org.gnome.Hamster.Frontend')
    def show_main_window(self):
        self.app.show_hamster_window()
        
    @dbus.service.method('org.gnome.Hamster.Frontend')
    def toggle_main_window(self):
        self.app.toggle_hamster_window()
        
    @dbus.service.method('org.gnome.Hamster.Frontend')
    def show_overview_window(self):
        dialogs.overview.show(True)
        
    @dbus.service.method('org.gnome.Hamster.Frontend')
    def show_statistics_window(self):
        dialogs.stats.show(True)
        
    @dbus.service.method('org.gnome.Hamster.Frontend')
    def show_preferences_window(self):
        dialogs.prefs.show(True)
        
    @dbus.service.method('org.gnome.Hamster.Frontend')
    def show_about_window(self):
        dialogs.about.show(True)
