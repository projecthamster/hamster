# -*- coding: utf-8 -*-

# Copyright (C) 2008 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2008 Pēteris Caune <cuu508 at gmail.com>

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


import gtk, gconf
from . import keybinder
from .configuration import runtime, conf

class Keybinder(object):
    def __init__(self):
        self.bound = False
        self.prevbinding = None

        self.key_combination = conf.get("keybinding")
        runtime.dispatcher.add_handler("conf_changed", self.on_conf_changed)

        self.bind()

    def on_conf_changed(self, event, data):
        key, value = data
        if key != "keybinding":
            return
        
        self.prevbinding = self.key_combination
        self.key_combination = value
        self.bind()

    def on_keybinding_activated(self):
        runtime.dispatcher.dispatch('keybinding_activated')

    def get_key_combination(self):
        return self.key_combination

    def bind(self):
        if self.bound:
            self.unbind()

        try:
            print 'Binding shortcut %s to popup hamster' % self.key_combination
            keybinder.tomboy_keybinder_bind(self.key_combination, self.on_keybinding_activated)
            self.bound = True
        except KeyError:
            # if the requested keybinding conflicts with an existing one, a KeyError will be thrown
            self.bound = False

        #self.emit('changed', self.bound)  TODO - revert to previous hotkey

    def unbind(self):
        try:
            print 'Unbinding shortcut %s to popup hamster' % self.prevbinding
            keybinder.tomboy_keybinder_unbind(self.prevbinding)
            self.bound = False
        except KeyError:
            # if the requested keybinding is not bound, a KeyError will be thrown
            pass


keybinder = Keybinder()

