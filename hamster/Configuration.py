# -*- coding: utf-8 -*-

# Copyright (C) 2004-2007 Johan Svedberg <johan@svedberg.com>

# This file is part of ontv.

# ontv is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# ontv is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with ontv; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import os.path
import sys
from gettext import gettext as _

import gconf

DIR_HAMSTER = "/apps/hamster-applet"

KEY_ENABLE_HOTKEYS              = "/general/enable_hotkeys"
KEY_SHOW_WINDOW_HOTKEY          = "/general/show_window_hotkey"

FUNCTION_SUFFIXES = {KEY_ENABLE_HOTKEYS:              'bool',
                     KEY_SHOW_WINDOW_HOTKEY:          'string'}

class Configuration(object):
    """Singleton representing the configuration"""

    instance = None

    def __new__(type, *args):
        if Configuration.instance is None:
            Configuration.instance = object.__new__(type)
            Configuration.instance.__init(*args)
        return Configuration.instance

    def __init(self, *args):
        self.base_dir = os.path.expanduser("~/.gnome2/hamster-applet")

        self.client = gconf.client_get_default()
        if self.client.dir_exists(DIR_HAMSTER):
            self.client.add_dir(DIR_HAMSTER, gconf.CLIENT_PRELOAD_RECURSIVE)
            self.debug = True
            self.__init_option_cache()
        else:
            #ed = ErrorDialog(_("Could not find configuration directory in GConf"), _("Please make sure that ontv.schemas was correctly installed."))
            #ed.run()
            print "Could not find configuration directory in GConf"
            sys.exit(1)

    def __init_option_cache(self):
        self.option_cache = {}
        for key in FUNCTION_SUFFIXES.keys():
            self.option_cache[key] = getattr(self, 'get_' +
                                             os.path.basename(key))(False)

    def add_notify(self, key, callback):
        self.client.notify_add(DIR_HAMSTER + key, callback)

    def add_show_window_hotkey_change_notify(self, callback):
        self.add_notify(KEY_SHOW_WINDOW_HOTKEY, callback)

    def add_enable_hotkeys_change_notify(self, callback):
        self.add_notify(KEY_ENABLE_HOTKEYS, callback)

    def __get_option(self, option, type=None):
        if self.debug:
            print '[GConf get]: %s%s' % (DIR_HAMSTER, option)
        if type:
            return getattr(self.client, 'get_' +
                           FUNCTION_SUFFIXES[option])(DIR_HAMSTER + option, type)
        else:
            return getattr(self.client, 'get_' +
                           FUNCTION_SUFFIXES[option])(DIR_HAMSTER + option)

    def __set_option(self, option, value, type=None):
        if self.debug:
            print '[GConf set]: %s%s=%s' % (DIR_HAMSTER, option, str(value))
        if type:
            getattr(self.client, 'set_' +
                    FUNCTION_SUFFIXES[option])(DIR_HAMSTER + option, type, value)
            self.option_cache[option] = value
        else:
            getattr(self.client, 'set_' +
                    FUNCTION_SUFFIXES[option])(DIR_HAMSTER + option, value)
            self.option_cache[option] = value

    def get_enable_hotkeys(self, use_cache=True):
        if use_cache:
            return self.option_cache[KEY_ENABLE_HOTKEYS]
        else:
            return self.__get_option(KEY_ENABLE_HOTKEYS)

    def set_enable_hotkeys(self, enable_hotkeys):
        self.__set_option(KEY_ENABLE_HOTKEYS, enable_hotkeys)

    enable_hotkeys = property(get_enable_hotkeys, set_enable_hotkeys)

    def get_show_window_hotkey(self, use_cache=True):
        if use_cache:
            return self.option_cache[KEY_SHOW_WINDOW_HOTKEY]
        else:
            return self.__get_option(KEY_SHOW_WINDOW_HOTKEY)

    def set_show_window_hotkey(self, show_window_hotkey):
        self.__set_option(KEY_SHOW_WINDOW_HOTKEY,
                          show_window_hotkey)

    show_window_hotkey = property(get_show_window_hotkey,
                                  set_show_window_hotkey)



# vim: set sw=4 et sts=4 tw=79 fo+=l:
