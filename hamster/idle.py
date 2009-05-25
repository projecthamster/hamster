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
from dbus.lowlevel import Message
import gconf

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


class DbusIdleListener(object):
    """
    Listen for idleness coming from org.gnome.ScreenSaver

    Monitors org.gnome.ScreenSaver for idleness. There are two types
    (that I know of), implicit (due to inactivity) and explicit (lock
    screen), that need to be handled differently. An implicit idle
    state should subtract the time-to-become-idle (as specified in the
    gconf) from the last activity, but an explicit idle state should
    not.

    The signals are inspected for the "SessionIdleChanged" and "Lock"
    members coming from the org.gnome.ScreenSaver interface and the
    is_idle, and is_screen_locked members are updated appropriately.
    """
    def __init__(self):
        self.screensaver_uri = "org.gnome.ScreenSaver"

        self.is_idle = False
        self.is_screen_locked = False

        try:
            self.bus = dbus.SessionBus()
        except:
            return 0
        # Listen for chatter on the screensaver interface.
        # We cannot just add additional match strings to narrow down
        # what we hear because match strings are ORed together.
        # E.g., if we were to make the match string
        # "interface='org.gnome.ScreenSaver', type='method_call'",
        # we would not get only screensaver's method calls, rather
        # we would get anything on the screensaver interface, as well
        # as any method calls on *any* interface. Therefore the
        # bus_inspector needs to do some additional filtering.
        self.bus.add_match_string_non_blocking(
                "interface='" + self.screensaver_uri + "'")

        self.bus.add_message_filter(self.bus_inspector)


    def bus_inspector(self, bus, message):
        """
        Inspect the bus for screensaver messages of interest

        Namely, we are watching for messages on the screensaver
        interface.  If it's a signal type for SessionIdleChanged,
        we set our internal is_idle state to that value (the signal
        is a boolean).  If its a method call with type "Lock" then
        the user requested to lock the screen so we set our internal
        lock state to true.

        When the SessionIdleChanged signal is false, it means we are
        returning from the locked/idle state, so both is_idle and
        is_screen_locked are reset to False.
        """
        # We only care about stuff on this interface.  Yes we did filter
        # for it above, but even so we still hear from ourselves
        # (hamster messages).
        if not message.get_interface() == self.screensaver_uri:
            return True

        # Signal type messages have a value of 4, and method_call type
        # ones have a value of 1.  I'm not sure how important it is to
        # verify that SessionIdleChanged on the screensaver interface
        # is actually a "signal" and not some other type of message
        # but I'll make sure just to be safe.  Same goes for the Lock
        # member.
        if message.get_member() == "SessionIdleChanged" and \
           message.get_type() == 4:
            if __debug__:
                print "SessionIdleChanged ->", message.get_args_list()
            idle_state = message.get_args_list()[0]
            if idle_state:
                self.is_idle = True
            else:
                self.is_idle = False
                self.is_screen_locked = False
        elif message.get_member() == "Lock" and \
             message.get_type() == 1:
            if __debug__:
                print "Screen Lock Requested"
            self.is_screen_locked = True
        
        return True


