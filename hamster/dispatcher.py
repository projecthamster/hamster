# - coding: utf-8 -

# Copyright (C) 2007, 2008 Patryk Zawadzki <patrys at pld-linux.org>

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


class Dispatcher(object):
    def __init__(self):
        self.handlers = {}

    def add_handler(self, event, method):
        if not self.handlers.has_key(event):
            self.handlers[event] = []
        if not method in self.handlers[event]:
            self.handlers[event].append(method)

    def del_handler(self, event, method):
        if self.handlers.has_key(event):
            if method in self.handlers[event]:
                self.handlers[event].remove(method)

    def dispatch(self, event, data = None):
        if self.handlers.has_key(event):
            for handler in self.handlers[event]:
                handler(event, data)
        else:
            print 'Missing handler for event %s' % event
