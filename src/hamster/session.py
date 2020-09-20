# -*- coding: utf-8 -*-

# Copyright (C) 2020 Sébastien Granjoux <seb.sfo@free.fr>

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

class DbusSessionListener(object):
    """Listen for GNOME manager end session event."""


    def end_session(self):
        """Override this method to do something at the end of a session.
        It must not attempt to interact with the user and will be given
        a maximum of ten seconds to perform the actions."""
        pass


    def __init__(self):
        """Connect to the GNOME manager session signals"""

        # Get SessionManager interface
        session_bus = dbus.SessionBus()
        session_manager = session_bus.get_object("org.gnome.SessionManager",
            "/org/gnome/SessionManager")
        self.__session_manager_iface = dbus.Interface(session_manager,
            dbus_interface="org.gnome.SessionManager")
        self.__client_id = self.__session_manager_iface.RegisterClient("", "")

        # Get SessionManager.ClientPrivate interface
        session_client = session_bus.get_object("org.gnome.SessionManager",
            self.__client_id)
        self.__session_client_private_iface = dbus.Interface(session_client,
            dbus_interface="org.gnome.SessionManager.ClientPrivate")

        # Connect to the needed signals
        session_bus.add_signal_receiver(self.__query_end_session_handler,
            signal_name = "QueryEndSession",
            dbus_interface = "org.gnome.SessionManager.ClientPrivate",
            bus_name = "org.gnome.SessionManager")

        session_bus.add_signal_receiver(self.__end_session_handler,
            signal_name = "EndSession",
            dbus_interface = "org.gnome.SessionManager.ClientPrivate",
            bus_name = "org.gnome.SessionManager")

        session_bus.add_signal_receiver(self.__stop_handler,
            signal_name = "Stop",
            dbus_interface = "org.gnome.SessionManager.ClientPrivate",
            bus_name = "org.gnome.SessionManager")


    def __query_end_session_handler(self, flags):
        """Inform that the session is about to end. It must reply with
        EndSessionResponse within one second telling if it is ok to proceed
        or not and why. If flags is true, the session will end anyway."""
        self.__session_client_private_iface.EndSessionResponse(True, "")

    def __end_session_handler(self, flags):
        """Inform that the session is about to end. It must reply with
        EndSessionResponse within ten seconds."""
        self.end_session()
        self.__session_client_private_iface.EndSessionResponse(True, "")

    def __stop_handler(self):
        """Remove from the session."""
        self.__session_manager_iface.UnregisterClient(self.__client_id)
