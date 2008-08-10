# - coding: utf-8 -

# Copyright (C) 2008 Patryk Zawadzki <patrys at pld-linux.org>

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

def getIdleSec():
    bus = dbus.SessionBus()
    try:
        gs = bus.get_object('org.gnome.ScreenSaver', '/org/gnome/ScreenSaver')
        return int(gs.GetSessionIdleTime())
    except:
        return 0
