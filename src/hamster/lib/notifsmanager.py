# - coding: utf-8 -

# Copyright (C) 2020 Sharaf Zaman <sharafzaz121@gmail.com>

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
logger = logging.getLogger(__name__)   # noqa: E402
import datetime
import dbus
import hamster.client

from gi.repository import Gtk
from gi.repository import GObject as gobject
from hamster.lib.configuration import conf


class Notification(object):
    def __init__(self):
        self.bus = dbus.SessionBus()
        self.appname = "Hamster Time Tracker"
        self.replace_id = 0
        self.summary = "Hamster Time Tracker"
        self.hints = {}
        self.actions = []
        self.data = {}
        self.timeout = -1

        info = Gtk.IconTheme().lookup_icon("hamster-time-tracker", 0, 0)
        self.icon = info.get_filename()

    def show(self, message):
        """
        Show notitification
        returns: True if successful
        """
        try:
            self.server = dbus.Interface(self.bus.get_object("org.freedesktop.Notifications",
                                                             "/org/freedesktop/Notifications"),
                                         dbus_interface="org.freedesktop.Notifications")
        except dbus.exceptions.DBusException as e:
            # TODO: Log?
            logger.error(e)
            logger.warning("Notifications will be disabled")
            return False

        try: 
            self.notif_id = self.server.Notify(
                self.appname,
                self.replace_id,
                self.icon,
                self.summary,
                message,
                self.actions,
                self.hints,
                self.timeout)
        except:
            return False 

        return True

    def close(self):
        try: self.server.CloseNotification(self.notif_id)
        except: pass



class NotificationsManager(gobject.GObject):
    def __init__(self):
        self.notify_interval = conf.notify_interval
        self.minutes_passed = 0
        self.notification = Notification()
        gobject.timeout_add_seconds(60, self.check_interval)

    def notify_interval_changed(self, value):
        self.minutes_passed = 0
        self.notify_interval = value

    def check_interval(self):
        if not conf.notifications_enabled:
            self.minutes_passed = 0
            return True

        self.minutes_passed += 1

        storage = hamster.client.Storage()
        facts = storage.get_todays_facts()

        if self.minutes_passed == self.notify_interval:
            # if the activity is still active
            if len(facts) > 0 and facts[-1].end_time is None:
                timedelta_secs = (datetime.datetime.now() - facts[-1].start_time).seconds
                hours, rem = divmod(timedelta_secs, 60 * 60)
                minutes, seconds = divmod(rem, 60)
                if hours != 0:
                    msg = str.format("Working on {} for {} hours and {} minutes", facts[-1].activity, hours, minutes)
                else:
                    msg = str.format("Working on {} for {} minutes", facts[-1].activity, minutes)
                self.notification.show(msg)
            elif conf.notify_on_idle:
                self.notification.show("No Activity")

            self.notification.close()

            self.minutes_passed = 0

        return True

    def send_test(self):
        return self.notification.show("This is a test notification!")


notifs_mgr = NotificationsManager()
