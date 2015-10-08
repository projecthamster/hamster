# - coding: utf-8 -

# Copyright (C) 2015 Aurelien Naldi <aurelien.naldi at gmail.com>

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

from gi.repository import GObject as gobject
from gi.repository import Wnck as wnck
import dbus

class WnckWatcher(gobject.GObject):
    """
    Listen for workspace changes with Wnck and forward them to the desktop integration agent.
    It handles all wnck-specific parts and forwards standardised signals, based on the screensaver helper.
    """
    __gsignals__ = {
        "workspace-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,gobject.TYPE_PYOBJECT))
    }
    def __init__(self):
        gobject.GObject.__init__(self)

        try:
            self.bus = dbus.SessionBus()
        except:
            return 0
        wnck.Screen.get_default().connect("active-workspace-changed", self.on_workspace_changed)


    def on_workspace_changed(self, screen, previous_workspace):
        try:
            workspace_id = screen.get_active_workspace().get_number()
            if previous_workspace:
                previous_workspace = previous_workspace.get_number()
        except:
            return
        
        self.emit('workspace-changed', previous_workspace, workspace_id)

