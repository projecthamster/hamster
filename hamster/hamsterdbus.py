# - coding: utf-8 -

# Copyright (C) 2008, J. Félix Ontañón <fontanon at emergya dot es>

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

import dbus
import dbus.service

HAMSTER_URI = "org.gnome.hamster"
HAMSTER_PATH = "/org/gnome/hamster"

class HamsterDbusController(dbus.service.Object):
    activity = "Undefined"
    fact = "Undefined"

    def __init__(self, bus_name):
        dbus.service.Object.__init__(self, bus_name, HAMSTER_PATH)

    @dbus.service.method(HAMSTER_URI)
    def get_activity(self):
        return self.activity

    @dbus.service.signal(HAMSTER_URI)
    def update_activity(self, activity):
	self.activity = activity

    @dbus.service.method(HAMSTER_URI)
    def get_fact(self):
        return self.fact

    @dbus.service.signal(HAMSTER_URI)
    def update_fact(self, fact):
	self.fact = fact
