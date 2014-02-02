# - coding: utf-8 -

# Copyright (C) 2007-2012 Toms Baugis <toms.baugis@gmail.com>

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

import datetime as dt
from calendar import timegm
import logging
from gi.repository import GObject as gobject


from hamster import idle
from hamster.lib.configuration import conf
from hamster.lib import trophies
import dbus


class DesktopIntegrations(object):
    def __init__(self, storage):
        self.storage = storage # can't use client as then we get in a dbus loop
        self._last_notification = None

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()

        self.conf_enable_timeout = conf.get("enable_timeout")
        self.conf_notify_on_idle = conf.get("notify_on_idle")
        self.conf_notify_interval = conf.get("notify_interval")
        conf.connect('conf-changed', self.on_conf_changed)

        self.idle_listener = idle.DbusIdleListener()
        self.idle_listener.connect('idle-changed', self.on_idle_changed)

        gobject.timeout_add_seconds(60, self.check_hamster)


    def check_hamster(self):
        """refresh hamster every x secs - load today, check last activity etc."""
        try:
            # can't use the client because then we end up in a dbus loop
            # as this is initiated in storage
            todays_facts = self.storage._Storage__get_todays_facts()
            self.check_user(todays_facts)
            trophies.check_ongoing(todays_facts)
        except Exception, e:
            logging.error("Error while refreshing: %s" % e)
        finally:  # we want to go on no matter what, so in case of any error we find out about it sooner
            return True


    def check_user(self, todays_facts):
        """check if we need to notify user perhaps"""
        interval = self.conf_notify_interval
        if interval <= 0 or interval >= 121:
            return

        now = dt.datetime.now()
        message = None

        last_activity = todays_facts[-1] if todays_facts else None

        # update duration of current task
        if last_activity and not last_activity['end_time']:
            delta = now - last_activity['start_time']
            duration = delta.seconds /  60

            if duration and duration % interval == 0:
                message = _(u"Working on %s") % last_activity['name']
                self.notify_user(message)

        elif self.conf_notify_on_idle:
            #if we have no last activity, let's just calculate duration from 00:00
            if (now.minute + now.hour * 60) % interval == 0:
                self.notify_user(_(u"No activity"))


    def notify_user(self, summary="", details=""):
        if not hasattr(self, "_notification_conn"):
            self._notification_conn = dbus.Interface(self.bus.get_object('org.freedesktop.Notifications',
                                                                         '/org/freedesktop/Notifications',
                                                                           follow_name_owner_changes=True),
                                                           dbus_interface='org.freedesktop.Notifications')
        conn = self._notification_conn

        notification = conn.Notify("Project Hamster",
                                   self._last_notification or 0,
                                   "hamster-time-tracker",
                                   summary,
                                   details,
                                   [],
                                   {"urgency": dbus.Byte(0), "transient" : True},
                                   -1)
        self._last_notification = notification


    def on_idle_changed(self, event, state):
        # state values: 0 = active, 1 = idle
        if state == 1 and self.conf_enable_timeout:
            idle_from = self.idle_listener.getIdleFrom()
            idle_from = timegm(idle_from.timetuple())
            self.storage.StopTracking(idle_from)


    def on_conf_changed(self, event, key, value):
        if hasattr(self, "conf_%s" % key):
            setattr(self, "conf_%s" % key, value)
