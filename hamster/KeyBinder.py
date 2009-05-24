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
import hamster, hamster.keybinder
from hamster.Configuration import GconfStore
from hamster import dispatcher

class Keybinder(object):
    def __init__(self):
        self.config = GconfStore.get_instance()
        
        self.bound = False
        self.prevbinding = None
        
        self.key_combination = self.config.get_keybinding()
        if self.key_combination is None:
            # This is for uninstalled cases, the real default is in the schema
            self.key_combination = "<Super>H"
    
        dispatcher.add_handler("gconf_keybinding_changed", self.on_keybinding_changed)
        
        self.bind()
      
    def on_keybinding_changed(self, event, new_binding = None):
        self.prevbinding = self.key_combination
        self.key_combination = new_binding
        self.bind()

    def on_keybinding_activated(self):
        dispatcher.dispatch('keybinding_activated')
   
    def get_key_combination(self):
        return self.key_combination
   
    def bind(self):
        if self.bound:
            self.unbind()
         
        try:
            print 'Binding shortcut %s to popup hamster' % self.key_combination
            hamster.keybinder.tomboy_keybinder_bind(self.key_combination, self.on_keybinding_activated)
            self.bound = True
        except KeyError:
            # if the requested keybinding conflicts with an existing one, a KeyError will be thrown
            self.bound = False
        
        #self.emit('changed', self.bound)  TODO - revert to previous hotkey
               
    def unbind(self):
        try:
            print 'Unbinding shortcut %s to popup hamster' % self.prevbinding
            hamster.keybinder.tomboy_keybinder_unbind(self.prevbinding)
            self.bound = False
        except KeyError:
            # if the requested keybinding is not bound, a KeyError will be thrown
            pass

if gtk.pygtk_version < (2,8,0):
    gobject.type_register(Keybinder)

keybinder = Keybinder()

def get_hamster_keybinder():
    return keybinder
