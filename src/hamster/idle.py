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

import logging
import dbus
from dbus.lowlevel import Message
import gconf
import datetime as dt
import gobject

class DbusIdleListener(gobject.GObject):
    """
    Listen for idleness coming from org.gnome.ScreenSaver

    Monitors org.gnome.ScreenSaver for idleness. There are two types,
    implicit (due to inactivity) and explicit (lock screen), that need to be
    handled differently. An implicit idle state should subtract the
    time-to-become-idle (as specified in the gconf) from the last activity,
    but an explicit idle state should not.

    The signals are inspected for the "ActiveChanged" and "Lock"
    members coming from the org.gnome.ScreenSaver interface and the
    and is_screen_locked members are updated appropriately.
    """
    __gsignals__ = {
        "idle-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    }
    def __init__(self):
        gobject.GObject.__init__(self)

        self.screensaver_uri = "org.gnome.ScreenSaver"
        self.screen_locked = False
        self.idle_from = None
        self.timeout_minutes = 0 # minutes after session is considered idle
        self.idle_was_there = False # a workaround variable for pre 2.26

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
        self.bus.add_match_string_non_blocking("interface='%s'" %
                                                           self.screensaver_uri)
        self.bus.add_message_filter(self.bus_inspector)


    def bus_inspector(self, bus, message):
        """
        Inspect the bus for screensaver messages of interest
        """

        # We only care about stuff on this interface.  We did filter
        # for it above, but even so we still hear from ourselves
        # (hamster messages).
        if message.get_interface() != self.screensaver_uri:
            return True

        member = message.get_member()

        if member in ("SessionIdleChanged", "ActiveChanged"):
            logging.debug("%s -> %s" % (member, message.get_args_list()))

            idle_state = message.get_args_list()[0]
            if idle_state:
                self.idle_from = dt.datetime.now()

                # from gnome screensaver 2.24 to 2.28 they have switched
                # configuration keys and signal types.
                # luckily we can determine key by signal type
                if member == "SessionIdleChanged":
                    delay_key = "/apps/gnome-screensaver/idle_delay"
                else:
                    delay_key = "/desktop/gnome/session/idle_delay"

                client = gconf.client_get_default()
                self.timeout_minutes = client.get_int(delay_key)

            else:
                self.screen_locked = False
                self.idle_from = None

            if member == "ActiveChanged":
                # ActiveChanged comes before SessionIdleChanged signal
                # as a workaround for pre 2.26, we will wait a second - maybe
                # SessionIdleChanged signal kicks in
                def dispatch_active_changed(idle_state):
                    if not self.idle_was_there:
                        self.emit('idle-changed', idle_state)
                    self.idle_was_there = False

                gobject.timeout_add_seconds(1, dispatch_active_changed, idle_state)

            else:
                # dispatch idle status change to interested parties
                self.idle_was_there = True
                self.emit('idle-changed', idle_state)

        elif member == "Lock":
            # in case of lock, lock signal will be sent first, followed by
            # ActiveChanged and SessionIdle signals
            logging.debug("Screen Lock Requested")
            self.screen_locked = True

        return


    def getIdleFrom(self):
        if not self.idle_from:
            return dt.datetime.now()

        if self.screen_locked:
            return self.idle_from
        else:
            # Only subtract idle time from the running task when
            # idleness is due to time out, not a screen lock.
            return self.idle_from - dt.timedelta(minutes = self.timeout_minutes)
