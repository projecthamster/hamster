# -*- coding: utf-8 -*-

# Copyright (C) 2007, 2008 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>
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


import os
from os.path import join, exists, isdir, isfile, dirname, abspath, expanduser
from shutil import copy as copyfile
import gtk	 
from gtk import glade
import gettext
import locale
	 
# Autotools set the actual data_dir in defs.py
from db import Storage
import defs
from dispatcher import Dispatcher

# Init i18n
gettext.install("hamster-applet", unicode = True)

# Allow to use not installed hamster
UNINSTALLED_HAMSTER = False
def _check(path):
    return exists(path) and isdir(path) and isfile(path+"/AUTHORS")

name = join(dirname(__file__), '..')
if _check(name):
    UNINSTALLED_HAMSTER = True

# Sets SHARED_DATA_DIR to local copy, or the system location
# Typically shared data dir is /usr/share/hamster-applet
if UNINSTALLED_HAMSTER:
    SHARED_DATA_DIR = abspath(join(dirname(__file__), '..', 'data'))
else:
    SHARED_DATA_DIR = join(defs.DATA_DIR, "hamster-applet")
print "Data Dir: %s" % SHARED_DATA_DIR

USER_HAMSTER_DIR = expanduser("~/.gnome2/hamster-applet")
DB_FILE = 'hamster.db'
HAMSTER_DB = join(USER_HAMSTER_DIR, DB_FILE)
if not exists(USER_HAMSTER_DIR):
    try:
        os.makedirs(USER_HAMSTER_DIR, 0744)
    except Exception , msg:
        print 'Error:could not create user dir (%s): %s' % (USER_HAMSTER_DIR, msg)

#check if db is here
if not exists(HAMSTER_DB):
    print "Database not found in %s - installing default from %s!" % (HAMSTER_DB, SHARED_DATA_DIR)
    copyfile(join(SHARED_DATA_DIR, DB_FILE), HAMSTER_DB)

    #change also permissions - sometimes they are 444
    try:
        os.chmod(HAMSTER_DB, 0664)
    except Exception, msg:	
        print 'Error:could not change mode on %s!' % (HAMSTER_DB)

# Init storage

dispatcher = Dispatcher()
storage = None
trace_sql = False
    
# Path to images, icons
ART_DATA_DIR = join(SHARED_DATA_DIR, "art")


def __init_db():
    """work around the problem that we need hamster before setting
       locale info, but that triggers init of DB and thus sets strings
       before they have been localized"""
    global storage
    storage = Storage(dispatcher)
    
