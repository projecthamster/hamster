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
from hamster import workspace
from hamster.lib.configuration import conf
from hamster.lib import trophies
import dbus


class DesktopIntegrations(object):
    def __init__(self, storage):
        self.storage = storage # can't use client as then we get in a dbus loop
        self._last_notification = None
        self._saved = {}

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()

        self.conf_enable_timeout = conf.get("enable_timeout")
        self.conf_notify_on_idle = conf.get("notify_on_idle")
        self.conf_notify_interval = conf.get("notify_interval")
        self.conf_workspace_tracking = conf.get("workspace_tracking")
        conf.connect('conf-changed', self.on_conf_changed)

        self.idle_listener = idle.DbusIdleListener()
        self.idle_listener.connect('idle-changed', self.on_idle_changed)

        gobject.timeout_add_seconds(60, self.check_hamster)

        self.workspace_listener = workspace.WnckWatcher()
        self.workspace_listener.connect('workspace-changed', self.on_workspace_changed)


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
        if not self.conf_enable_timeout:
            if '__paused__' in self._saved:
                del self._saved['__paused__']
            return
        
        # state values: 0 = active, 1 = idle
        if state == 1:
            idle_from = self.idle_listener.getIdleFrom()
            idle_from = timegm(idle_from.timetuple())
            self.save_current('__paused__')
            self.storage.StopTracking(idle_from)
        elif '__paused__' in self._saved:
            self.restore('__paused__', delete=True)


    def on_workspace_changed(self, event, previous_workspace, current_workspace):
        if 'memory' not in self.conf_workspace_tracking:
            return
        
        if previous_workspace is not None:
            self.save_current( previous_workspace )
        self.restore(current_workspace)


    def on_conf_changed(self, event, key, value):
        if hasattr(self, "conf_%s" % key):
            setattr(self, "conf_%s" % key, value)


    def get_current(self):
        facts = self.storage.get_todays_facts()
        if facts:
            last = facts[-1]
            if not last['end_time']:
                name = last['name']
                category = last['category']
                return name,category


    def save_current(self, key):
        current = self.get_current()
        if current is not None:
            self._saved[key] = current
        elif key in self._saved:
            del self._saved[key]


    def restore(self, key, delete=False):
        activity,category = None,None
        if key in self._saved:
            activity, category = self._saved[key]            
            if delete:
                del self._saved[key]
        
        if not activity:
            self.storage.StopTracking(None)
            return
        
        if category:
            activity = '%s@%s' % (activity,category)
        
        self.storage.add_fact( activity, None, None)

