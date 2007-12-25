import os, sys
from os.path import join, exists, isdir, isfile, dirname, abspath, expanduser
from shutil import copy as copyfile
from hamster import db

import gtk, gnome.ui

# Autotools set the actual data_dir in defs.py
from defs import *

# Init i18n

import gettext
from gtk import glade
import locale

locale.setlocale(locale.LC_ALL, '')
for module in glade, gettext:
    module.bindtextdomain('hamster-applet')
    module.textdomain('hamster-applet')

import __builtin__
__builtin__._ = gettext.gettext

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

    
# Path to images, icons
ART_DATA_DIR = join(SHARED_DATA_DIR, "art")


"""upgrade DB to hamster version"""
version = db.fetchone("select version from version")["version"]

if version <2:
    """moving from fact_date, fact_time to start_time, end_time"""
    
    #create new table and copy data
    db.execute("""CREATE TABLE facts_new(id integer primary key,
                                         activity_id integer,
                                         start_time varchar2(12),
                                         end_time varchar2(12))""")
    
    db.execute("""INSERT INTO facts_new(id, activity_id, start_time)
                       SELECT id, activity_id, fact_date||fact_time from facts""")

    db.execute("DROP TABLE facts")
    db.execute("ALTER TABLE facts_new RENAME TO facts")

    # run through all facts and set the end time
    # if previous fact is not on the same date, then it means that it was the
    # last one in previous, so remove it
    # this logic saves our last entry from being deleted, which is good
    facts = db.fetchall("""SELECT id, activity_id, start_time,
                                  substr(start_time,1, 8) start_date
                             FROM facts
                             ORDER BY start_time""")
    prev_fact = None
    
    for fact in facts:
        if prev_fact:
            if prev_fact['start_date'] == fact['start_date']:
                db.execute("UPDATE facts SET end_time = ? where id = ?",
                           (fact['start_time'], prev_fact['id']))
            else:
                #otherwise that's the last entry of the day - remove it
                db.execute("delete from facts where id = ?", (prev_fact["id"],))
                
        prev_fact = fact

#it was kind of silly not to have datetimes in first place
if version <3:
    #create new table and copy data
    db.execute("""CREATE TABLE facts_new (id integer primary key,
                                          activity_id integer,
                                          start_time timestamp,
                                          end_time timestamp)""")
    
    db.execute("""INSERT INTO facts_new (id, activity_id, start_time, end_time)
                       SELECT id, activity_id,
                              substr(start_time,1,4) || "-"
                           || substr(start_time, 5, 2) || "-"
                           || substr(start_time, 7, 2) || " "
                           || substr(start_time, 9, 2) || ":"
                           || substr(start_time, 11, 2) || ":00",
                              substr(end_time,1,4) || "-"
                           || substr(end_time, 5, 2) || "-"
                           || substr(end_time, 7, 2) || " "
                           || substr(end_time, 9, 2) || ":"
                           || substr(end_time, 11, 2) || ":00"
                         FROM facts;
               """)

    db.execute("DROP TABLE facts")
    db.execute("ALTER TABLE facts_new RENAME TO facts")



#lock down current version
db.execute("update version set version=3")
