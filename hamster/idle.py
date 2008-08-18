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
import gconf

# TODO - since we don't allow to specify idle minutes, we should just listen
# to the SessionIdleChanged signal from org.gnome.Screensaver
def getIdleSec():
    try:
        bus = dbus.SessionBus()
        gs = bus.get_object('org.gnome.ScreenSaver', '/org/gnome/ScreenSaver')
        idle_time = gs.GetSessionIdleTime()
    except:
        return 0
    
    if idle_time > 0:
        # if we are in idle - grab gconf setting how much is considered idle
        client = gconf.client_get_default()
        idle_delay = client.get_int("/apps/gnome-screensaver/idle_delay")
        idle_time += idle_delay * 60 #delay is in minutes
    
    return idle_time

    