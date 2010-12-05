#!/usr/bin/env python

#
#  Copyright (C) 2010 Toms Baugis
#
#  Original code from Banshee control,
#  Copyright (C) 2009-2010 Jason Smith, Rico Tzschichholz
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import atexit
import gobject
import sys, os
from subprocess import Popen


import gtk
from docky.docky import DockyItem, DockySink
from signal import signal, SIGTERM
from sys import exit


from hamster import client
from hamster.lib import stuff, i18n
i18n.setup_i18n()


class DockyHamsterItem(DockyItem):
    def __init__(self, path):
        DockyItem.__init__(self, path)

        self.storage = client.Storage()
        self.storage.connect("facts-changed", lambda storage: self.refresh_hamster())
        self.storage.connect("activities-changed", lambda storage: self.refresh_hamster())

        self.id_map = {} #menu items

        self.update_text()
        self.add_actions()
        gobject.timeout_add_seconds(60, self.refresh_hamster)


    def refresh_hamster(self):
        try:
            self.update_text()
        finally:  # we want to go on no matter what, so in case of any error we find out about it sooner
            return True


    def update_text(self):
        today = self.storage.get_todays_facts()

        if today and today[-1].end_time is None:
            fact = today[-1]

            self.iface.SetText("%s - %s" % (fact.activity, fact.category))
            self.iface.SetBadgeText(stuff.format_duration(fact.delta, human=False))
        else:
            self.iface.SetText(_("No activity"))
            self.iface.ResetBadgeText()

    def add_menu_item(self, name, icon):
        menu_id = self.iface.AddMenuItem(name, icon, "")
        self.id_map[menu_id] = name

    def menu_pressed(self, menu_id):
        if self.id_map[menu_id] == _("Overview"):
            Popen(["hamster-time-tracker", "overview"])
        elif self.id_map[menu_id] == _("Preferences"):
            Popen(["hamster-time-tracker", "preferences"])

        self.add_actions() # TODO - figure out why is it that we have to regen all menu items after each click


    def add_actions(self):
        # first clear the menu
        for k, v in self.id_map.iteritems():
            self.iface.RemoveItem(k)

        self.id_map = {}
        # now add buttons
        self.add_menu_item(_("Overview"), "")
        self.add_menu_item(_("Preferences"), "preferences-desktop-personal")


class DockyHamsterSink(DockySink):
    def item_path_found(self, pathtoitem, item):
        if item.GetOwnsDesktopFile() and item.GetDesktopFile().endswith("hamster-time-tracker.desktop"):
            self.items[pathtoitem] = DockyHamsterItem(pathtoitem)

dockysink = DockyHamsterSink()

def cleanup():
    dockysink.dispose()

if __name__ == "__main__":
    mainloop = gobject.MainLoop(is_running=True)

    atexit.register (cleanup)
    signal(SIGTERM, lambda signum, stack_frame: exit(1))

    while mainloop.is_running():
        mainloop.run()
