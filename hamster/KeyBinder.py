# -*- coding: utf-8 -*-
# This file is part of projecthamster, and originally, i believe - tomboy


import sys

import gobject

import hamster.keybinder

class KeyBinder(gobject.GObject):
    __gproperties__ = {"show_window_hotkey": (str, "Show window hotkey",
                       "The hotkey for showing the window", "",
                       gobject.PARAM_READWRITE),
                       "show_search_program_hotkey": (str, "Show search \
                       program hotkey", "The hotkey for showing search \
                       program", "", gobject.PARAM_READWRITE)}

    __gsignals__ = {"activated": (gobject.SIGNAL_RUN_LAST, None,
                                  (str, gobject.TYPE_ULONG))}

    def __init__(self, config):
        gobject.GObject.__init__(self)
        self.config = config
        self.props.show_window_hotkey = config.show_window_hotkey
        self.props.show_search_program_hotkey = config.show_search_program_hotkey

    def do_get_property(self, property):
        if property.name == "show-window-hotkey":
            return self.show_window_hotkey
        elif property.name == "show-search-program-hotkey":
            return self.show_search_program_hotkey

    def do_set_property(self, property, value):
        if property.name == "show-window-hotkey":
            self.show_window_hotkey = value
        elif property.name == "show-search-program-hotkey":
            self.show_search_program_hotkey = value
        self.bind(value, property.name)

    def bind(self, key, name):
        try:
            hamster.keybinder.tomboy_keybinder_bind(key, self.__bind_activated,
                                                 name)
            if self.config.debug:
                print "Binded key \"%s\" to %s." % (key, name)
        except KeyError, ke:
            print >> sys.stderr, ke

    def __bind_activated(self, name):
        self.emit("activated", name,
                  hamster.keybinder.tomboy_keybinder_get_current_event_time())

    def unbind(self, key):
        try:
            hamster.keybinder.tomboy_keybinder_unbind(key)
            if self.config.debug:
                print "Unbinded key \"%s\"." % (key)
        except KeyError, ke:
            print >> sys.stderr, ke

# vim: set sw=4 et sts=4 tw=79 fo+=l:
