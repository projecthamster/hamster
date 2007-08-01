import os, sys
from os.path import join, exists, isdir, isfile, dirname, abspath, expanduser

import gtk

# Autotools set the actual data_dir in defs.py
from defs import *

try:
    # Allows to load uninstalled .la libs
    import ltihooks
except ImportError:
    pass

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
    SHARED_DATA_DIR = join(DATA_DIR, "hamster-applet")
print "Data Dir: %s" % SHARED_DATA_DIR

USER_HAMSTER_DIR = expanduser("~/.gnome2/hamster-applet")
if not exists(USER_HAMSTER_DIR):
    try:
        os.makedirs(USER_HAMSTER_DIR, 0744)
    except Exception , msg:
        print 'Error:could not create user dir (%s): %s' % (USER_HAMSTER_DIR, msg)

# Path to images, icons
ART_DATA_DIR = join(SHARED_DATA_DIR, "art")
