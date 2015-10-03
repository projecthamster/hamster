# - coding: utf-8 -

# Copyright (C) 2007-2009, 2012, 2014 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>

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


"""separate file for database operations"""
import logging

try:
    import sqlite3 as sqlite
except ImportError:
    try:
        logging.warn("Using sqlite2")
        from pysqlite2 import dbapi2 as sqlite
    except ImportError:
        logging.error("Neither sqlite3 nor pysqlite2 found")
        raise

import os, time
import datetime
import storage
from shutil import copy as copyfile
import itertools
import datetime as dt
try:
    from gi.repository import Gio as gio
except ImportError:
    print "Could not import gio - requires pygobject. File monitoring will be disabled"
    gio = None

from hamster.lib import Fact
from hamster.lib import trophies

class Storage(storage.Storage):
    con = None # Connection will be created on demand
    def __init__(self, unsorted_localized="Unsorted", database_dir=None):
        """
        XXX - you have to pass in name for the uncategorized category
        Delayed setup so we don't do everything at the same time
        """
        storage.Storage.__init__(self)

        self._unsorted_localized = unsorted_localized

        self.__con = None
        self.__cur = None
        self.__last_etag = None


        self.db_path = self.__init_db_file(database_dir)

        if gio:
            # add file monitoring so the app does not have to be restarted
            # when db file is rewritten
            def on_db_file_change(monitor, gio_file, event_uri, event):
                if event == gio.FileMonitorEvent.CHANGES_DONE_HINT:
                    if gio_file.query_info(gio.FILE_ATTRIBUTE_ETAG_VALUE,
                                           gio.FileQueryInfoFlags.NONE,
                                           None).get_etag() == self.__last_etag:
                        # ours
                        return
                elif event == gio.FileMonitorEvent.CREATED:
                    # treat case when instead of a move, a remove and create has been performed
                    self.con = None

                if event in (gio.FileMonitorEvent.CHANGES_DONE_HINT, gio.FileMonitorEvent.CREATED):
                    print "DB file has been modified externally. Calling all stations"
                    self.dispatch_overwrite()

                    # plan "b" – synchronize the time tracker's database from external source while the tracker is running
                    if trophies:
                        trophies.unlock("plan_b")


            self.__database_file = gio.File.new_for_path(self.db_path)
            self.__db_monitor = self.__database_file.monitor_file(gio.FileMonitorFlags.WATCH_MOUNTS | \
                                                                  gio.FileMonitorFlags.SEND_MOVED,
                                                                  None)
            self.__db_monitor.connect("changed", on_db_file_change)

        self.run_fixtures()

    def __init_db_file(self, database_dir):
        if not database_dir:
            try:
                from xdg.BaseDirectory import xdg_data_home
                database_dir = os.path.realpath(os.path.join(xdg_data_home, "hamster-applet"))
            except ImportError:
                print "Could not import xdg - will store hamster.db in home folder"
                database_dir = os.path.realpath(os.path.expanduser("~"))

        if not os.path.exists(database_dir):
            os.makedirs(database_dir, 0744)

        # handle the move to xdg_data_home
        old_db_file = os.path.expanduser("~/.gnome2/hamster-applet/hamster.db")
        new_db_file = os.path.join(database_dir, "hamster.db")
        if os.path.exists(old_db_file):
            if os.path.exists(new_db_file):
                logging.info("Have two database %s and %s" % (new_db_file, old_db_file))
            else:
                os.rename(old_db_file, new_db_file)

        db_path = os.path.join(database_dir, "hamster.db")

        # check if we have a database at all
        if not os.path.exists(db_path):
            # if not there, copy from the defaults
            try:
                from hamster import defs
                data_dir = os.path.join(defs.DATA_DIR, "hamster-time-tracker")
            except:
                # if defs is not there, we are running from sources
                module_dir = os.path.dirname(os.path.realpath(__file__))
                if os.path.exists(os.path.join(module_dir, "data")):
                    # running as flask app. XXX - detangle
                    data_dir = os.path.join(module_dir, "data")
                else:
                    data_dir = os.path.join(module_dir, '..', '..', 'data')

            data_dir = os.path.realpath(data_dir)

            logging.info("Database not found in %s - installing default from %s!" % (db_path, data_dir))
            copyfile(os.path.join(data_dir, 'hamster.db'), db_path)

            #change also permissions - sometimes they are 444
            os.chmod(db_path, 0664)

        return db_path


    def register_modification(self):
        if gio:
            # db.execute calls this so we know that we were the ones
            # that modified the DB and no extra refesh is not needed
            self.__last_etag = self.__database_file.query_info(gio.FILE_ATTRIBUTE_ETAG_VALUE,
                                                               gio.FileQueryInfoFlags.NONE,
                                                               None).get_etag()

    #tags, here we come!
    def __get_tags(self, only_autocomplete = False):
        if only_autocomplete:
            return self.fetchall("select * from tags where autocomplete != 'false' order by name")
        else:
            return self.fetchall("select * from tags order by name")

    def __get_tag_ids(self, tags):
        """look up tags by their name. create if not found"""

        db_tags = self.fetchall("select * from tags where name in (%s)"
                                            % ",".join(["?"] * len(tags)), tags) # bit of magic here - using sqlites bind variables

        changes = False

        # check if any of tags needs resurrection
        set_complete = [str(tag["id"]) for tag in db_tags if tag["autocomplete"] == "false"]
        if set_complete:
            changes = True
            self.execute("update tags set autocomplete='true' where id in (%s)" % ", ".join(set_complete))


        found_tags = [tag["name"] for tag in db_tags]

        add = set(tags) - set(found_tags)
        if add:
            statement = "insert into tags(name) values(?)"

            self.execute([statement] * len(add), [(tag,) for tag in add])

            return self.__get_tag_ids(tags)[0], True # all done, recurse
        else:
            return db_tags, changes

    def __update_autocomplete_tags(self, tags):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]  # split by comma

        #first we will create new ones
        tags, changes = self.__get_tag_ids(tags)
        tags = [tag["id"] for tag in tags]

        #now we will find which ones are gone from the list
        query = """
                    SELECT b.id as id, b.autocomplete, count(a.fact_id) as occurences
                      FROM tags b
                 LEFT JOIN fact_tags a on a.tag_id = b.id
                     WHERE b.id not in (%s)
                  GROUP BY b.id
                """ % ",".join(["?"] * len(tags)) # bit of magic here - using sqlites bind variables

        gone = self.fetchall(query, tags)

        to_delete = [str(tag["id"]) for tag in gone if tag["occurences"] == 0]
        to_uncomplete = [str(tag["id"]) for tag in gone if tag["occurences"] > 0 and tag["autocomplete"] == "true"]

        if to_delete:
            self.execute("delete from tags where id in (%s)" % ", ".join(to_delete))

        if to_uncomplete:
            self.execute("update tags set autocomplete='false' where id in (%s)" % ", ".join(to_uncomplete))

        return changes or len(to_delete + to_uncomplete) > 0

    def __get_categories(self):
        return self.fetchall("SELECT id, name FROM categories ORDER BY lower(name)")

    def __update_activity(self, id, name, category_id):
        query = """
                   UPDATE activities
                       SET name = ?,
                           search_name = ?,
                           category_id = ?
                     WHERE id = ?
        """
        self.execute(query, (name, name.lower(), category_id, id))

        affected_ids = [res[0] for res in self.fetchall("select id from facts where activity_id = ?", (id,))]
        self.__remove_index(affected_ids)


    def __change_category(self, id, category_id):
        # first check if we don't have an activity with same name before us
        activity = self.fetchone("select name from activities where id = ?", (id, ))
        existing_activity = self.__get_activity_by_name(activity['name'], category_id)

        if existing_activity and id == existing_activity['id']: # we are already there, go home
            return False

        if existing_activity: #ooh, we have something here!
            # first move all facts that belong to movable activity to the new one
            update = """
                       UPDATE facts
                          SET activity_id = ?
                        WHERE activity_id = ?
            """

            self.execute(update, (existing_activity['id'], id))

            # and now get rid of our friend
            self.__remove_activity(id)

        else: #just moving
            statement = """
                       UPDATE activities
                          SET category_id = ?
                        WHERE id = ?
            """

            self.execute(statement, (category_id, id))

        affected_ids = [res[0] for res in self.fetchall("select id from facts where activity_id = ?", (id,))]
        if existing_activity:
            affected_ids.extend([res[0] for res in self.fetchall("select id from facts where activity_id = ?", (existing_activity['id'],))])
        self.__remove_index(affected_ids)

        return True

    def __add_category(self, name):
        query = """
                   INSERT INTO categories (name, search_name)
                        VALUES (?, ?)
        """
        self.execute(query, (name, name.lower()))
        return self.__last_insert_rowid()

    def __update_category(self, id,  name):
        if id > -1: # Update, and ignore unsorted, if that was somehow triggered
            update = """
                       UPDATE categories
                           SET name = ?, search_name = ?
                         WHERE id = ?
            """
            self.execute(update, (name, name.lower(), id))

        affected_query = """
            SELECT id
              FROM facts
             WHERE activity_id in (SELECT id FROM activities where category_id=?)
        """
        affected_ids = [res[0] for res in self.fetchall(affected_query, (id,))]
        self.__remove_index(affected_ids)


    def __get_activity_by_name(self, name, category_id = None, resurrect = True):
        """get most recent, preferably not deleted activity by it's name"""

        if category_id:
            query = """
                       SELECT a.id, a.name, a.deleted, coalesce(b.name, ?) as category
                         FROM activities a
                    LEFT JOIN categories b ON category_id = b.id
                        WHERE lower(a.name) = lower(?)
                          AND category_id = ?
                     ORDER BY a.deleted, a.id desc
                        LIMIT 1
            """

            res = self.fetchone(query, (self._unsorted_localized, name, category_id))
        else:
            query = """
                       SELECT a.id, a.name, a.deleted, coalesce(b.name, ?) as category
                         FROM activities a
                    LEFT JOIN categories b ON category_id = b.id
                        WHERE lower(a.name) = lower(?)
                     ORDER BY a.deleted, a.id desc
                        LIMIT 1
            """
            res = self.fetchone(query, (self._unsorted_localized, name, ))

        if res:
            keys = ('id', 'name', 'deleted', 'category')
            res = dict([(key, res[key]) for key in keys])
            res['deleted'] = res['deleted'] or False

            # if the activity was marked as deleted, resurrect on first call
            # and put in the unsorted category
            if res['deleted'] and resurrect:
                update = """
                            UPDATE activities
                               SET deleted = null, category_id = -1
                             WHERE id = ?
                        """
                self.execute(update, (res['id'], ))

            return res

        return None

    def __get_category_id(self, name):
        """returns category by it's name"""

        query = """
                   SELECT id from categories
                    WHERE lower(name) = lower(?)
                 ORDER BY id desc
                    LIMIT 1
        """

        res = self.fetchone(query, (name, ))

        if res:
            return res['id']

        return None

    def __get_fact(self, id):
        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS name, b.id as activity_id,
                          coalesce(c.name, ?) as category, coalesce(c.id, -1) as category_id,
                          e.name as tag
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                LEFT JOIN categories c ON b.category_id = c.id
                LEFT JOIN fact_tags d ON d.fact_id = a.id
                LEFT JOIN tags e ON e.id = d.tag_id
                    WHERE a.id = ?
                 ORDER BY e.name
        """

        return self.__group_tags(self.fetchall(query, (self._unsorted_localized, id)))[0]

    def __group_tags(self, facts):
        """put the fact back together and move all the unique tags to an array"""
        if not facts: return facts  #be it None or whatever

        grouped_facts = []
        for fact_id, fact_tags in itertools.groupby(facts, lambda f: f["id"]):
            fact_tags = list(fact_tags)

            # first one is as good as the last one
            grouped_fact = fact_tags[0]

            # we need dict so we can modify it (sqlite.Row is read only)
            # in python 2.5, sqlite does not have keys() yet, so we hardcode them (yay!)
            keys = ["id", "start_time", "end_time", "description", "name",
                    "activity_id", "category", "tag"]
            grouped_fact = dict([(key, grouped_fact[key]) for key in keys])

            grouped_fact["tags"] = [ft["tag"] for ft in fact_tags if ft["tag"]]
            grouped_facts.append(grouped_fact)
        return grouped_facts


    def __touch_fact(self, fact, end_time = None):
        end_time = end_time or dt.datetime.now()
        # tasks under one minute do not count
        if end_time - fact['start_time'] < datetime.timedelta(minutes = 1):
            self.__remove_fact(fact['id'])
        else:
            end_time = end_time.replace(microsecond = 0)
            query = """
                       UPDATE facts
                          SET end_time = ?
                        WHERE id = ?
            """
            self.execute(query, (end_time, fact['id']))

    def __squeeze_in(self, start_time):
        """ tries to put task in the given date
            if there are conflicts, we will only truncate the ongoing task
            and replace it's end part with our activity """

        # we are checking if our start time is in the middle of anything
        # or maybe there is something after us - so we know to adjust end time
        # in the latter case go only few hours ahead. everything else is madness, heh
        query = """
                   SELECT a.*, b.name
                     FROM facts a
                LEFT JOIN activities b on b.id = a.activity_id
                    WHERE ((start_time < ? and end_time > ?)
                           OR (start_time > ? and start_time < ? and end_time is null)
                           OR (start_time > ? and start_time < ?))
                 ORDER BY start_time
                    LIMIT 1
                """
        fact = self.fetchone(query, (start_time, start_time,
                                     start_time - dt.timedelta(hours = 12),
                                     start_time, start_time,
                                     start_time + dt.timedelta(hours = 12)))
        end_time = None
        if fact:
            if start_time > fact["start_time"]:
                #we are in middle of a fact - truncate it to our start
                self.execute("UPDATE facts SET end_time=? WHERE id=?",
                             (start_time, fact["id"]))

            else: #otherwise we have found a task that is after us
                end_time = fact["start_time"]

        return end_time

    def __solve_overlaps(self, start_time, end_time):
        """finds facts that happen in given interval and shifts them to
        make room for new fact
        """
        if end_time is None or start_time is None:
            return

        # possible combinations and the OR clauses that catch them
        # (the side of the number marks if it catches the end or start time)
        #             |----------------- NEW -----------------|
        #      |--- old --- 1|   |2 --- old --- 1|   |2 --- old ---|
        # |3 -----------------------  big old   ------------------------ 3|
        query = """
                   SELECT a.*, b.name, c.name as category
                     FROM facts a
                LEFT JOIN activities b on b.id = a.activity_id
                LEFT JOIN categories c on b.category_id = c.id
                    WHERE (end_time > ? and end_time < ?)
                       OR (start_time > ? and start_time < ?)
                       OR (start_time < ? and end_time > ?)
                 ORDER BY start_time
                """
        conflicts = self.fetchall(query, (start_time, end_time,
                                          start_time, end_time,
                                          start_time, end_time))

        for fact in conflicts:
            # won't eliminate as it is better to have overlapping entries than loosing data
            if start_time < fact["start_time"] and end_time > fact["end_time"]:
                continue

            # split - truncate until beginning of new entry and create new activity for end
            if fact["start_time"] < start_time < fact["end_time"] and \
               fact["start_time"] < end_time < fact["end_time"]:

                logging.info("splitting %s" % fact["name"])
                # truncate until beginning of the new entry
                self.execute("""UPDATE facts
                                   SET end_time = ?
                                 WHERE id = ?""", (start_time, fact["id"]))
                fact_name = fact["name"]

                # create new fact for the end
                new_fact = Fact(fact["name"],
                                category = fact["category"],
                                description = fact["description"])
                new_fact_id = self.__add_fact(new_fact.serialized_name(), end_time, fact["end_time"])

                # copy tags
                tag_update = """INSERT INTO fact_tags(fact_id, tag_id)
                                     SELECT ?, tag_id
                                       FROM fact_tags
                                      WHERE fact_id = ?"""
                self.execute(tag_update, (new_fact_id, fact["id"])) #clone tags

                if trophies:
                    trophies.unlock("split")

            # overlap start
            elif start_time < fact["start_time"] < end_time:
                logging.info("Overlapping start of %s" % fact["name"])
                self.execute("UPDATE facts SET start_time=? WHERE id=?",
                             (end_time, fact["id"]))

            # overlap end
            elif start_time < fact["end_time"] < end_time:
                logging.info("Overlapping end of %s" % fact["name"])
                self.execute("UPDATE facts SET end_time=? WHERE id=?",
                             (start_time, fact["id"]))


    def __add_fact(self, serialized_fact, start_time, end_time = None, temporary = False):
        fact = Fact(serialized_fact,
                    start_time = start_time,
                    end_time = end_time)

        start_time = start_time or fact.start_time
        end_time = end_time or fact.end_time

        if not fact.activity or start_time is None:  # sanity check
            return 0


        # get tags from database - this will create any missing tags too
        tags = [(tag['id'], tag['name'], tag['autocomplete']) for tag in self.get_tag_ids(fact.tags)]

        # now check if maybe there is also a category
        category_id = None
        if fact.category:
            category_id = self.__get_category_id(fact.category)
            if not category_id:
                category_id = self.__add_category(fact.category)

                if trophies:
                    trophies.unlock("no_hands")

        # try to find activity, resurrect if not temporary
        activity_id = self.__get_activity_by_name(fact.activity,
                                                  category_id,
                                                  resurrect = not temporary)
        if not activity_id:
            activity_id = self.__add_activity(fact.activity,
                                              category_id, temporary)
        else:
            activity_id = activity_id['id']

        # if we are working on +/- current day - check the last_activity
        if (dt.timedelta(days=-1) <= dt.datetime.now() - start_time <= dt.timedelta(days=1)):
            # pull in previous facts
            facts = self.__get_todays_facts()

            previous = None
            if facts and facts[-1]["end_time"] == None:
                previous = facts[-1]

            if previous and previous['start_time'] <= start_time:
                # check if maybe that is the same one, in that case no need to restart
                if previous["activity_id"] == activity_id \
                   and set(previous["tags"]) == set([tag[1] for tag in tags]) \
                   and (previous["description"] or "") == (fact.description or ""):
                    return None

                # if no description is added
                # see if maybe previous was too short to qualify as an activity
                if not previous["description"] \
                   and 60 >= (start_time - previous['start_time']).seconds >= 0:
                    self.__remove_fact(previous['id'])

                    # now that we removed the previous one, see if maybe the one
                    # before that is actually same as the one we want to start
                    # (glueing)
                    if len(facts) > 1 and 60 >= (start_time - facts[-2]['end_time']).seconds >= 0:
                        before = facts[-2]
                        if before["activity_id"] == activity_id \
                           and set(before["tags"]) == set([tag[1] for tag in tags]):
                            # resume and return
                            update = """
                                       UPDATE facts
                                          SET end_time = null
                                        WHERE id = ?
                            """
                            self.execute(update, (before["id"],))

                            return before["id"]
                else:
                    # otherwise stop
                    update = """
                               UPDATE facts
                                  SET end_time = ?
                                WHERE id = ?
                    """
                    self.execute(update, (start_time, previous["id"]))


        # done with the current activity, now we can solve overlaps
        if not end_time:
            end_time = self.__squeeze_in(start_time)
        else:
            self.__solve_overlaps(start_time, end_time)


        # finally add the new entry
        insert = """
                    INSERT INTO facts (activity_id, start_time, end_time, description)
                               VALUES (?, ?, ?, ?)
        """
        self.execute(insert, (activity_id, start_time, end_time, fact.description))

        fact_id = self.__last_insert_rowid()

        #now link tags
        insert = ["insert into fact_tags(fact_id, tag_id) values(?, ?)"] * len(tags)
        params = [(fact_id, tag[0]) for tag in tags]
        self.execute(insert, params)

        self.__remove_index([fact_id])
        return fact_id

    def __last_insert_rowid(self):
        return self.fetchone("SELECT last_insert_rowid();")[0]


    def __get_todays_facts(self):
        try:
            from hamster.lib.configuration import conf
            day_start = conf.get("day_start_minutes")
        except:
            day_start = 5 * 60 # default day start to 5am
        day_start = dt.time(day_start / 60, day_start % 60)
        today = (dt.datetime.now() - dt.timedelta(hours = day_start.hour,
                                                  minutes = day_start.minute)).date()
        return self.__get_facts(today)


    def __get_facts(self, date, end_date = None, search_terms = ""):
        try:
            from hamster.lib.configuration import conf
            day_start = conf.get("day_start_minutes")
        except:
            day_start = 5 * 60 # default day start to 5am
        day_start = dt.time(day_start / 60, day_start % 60)

        split_time = day_start
        datetime_from = dt.datetime.combine(date, split_time)

        end_date = end_date or date
        datetime_to = dt.datetime.combine(end_date, split_time) + dt.timedelta(days = 1)

        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS name, b.id as activity_id,
                          coalesce(c.name, ?) as category,
                          e.name as tag
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                LEFT JOIN categories c ON b.category_id = c.id
                LEFT JOIN fact_tags d ON d.fact_id = a.id
                LEFT JOIN tags e ON e.id = d.tag_id
                    WHERE (a.end_time >= ? OR a.end_time IS NULL) AND a.start_time <= ?
        """

        if search_terms:
            # check if we need changes to the index
            self.__check_index(datetime_from, datetime_to)

            # flip the query around when it starts with "not "
            reverse_search_terms = search_terms.lower().startswith("not ")
            if reverse_search_terms:
                search_terms = search_terms[4:]

            search_terms = search_terms.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_').replace("'", "''")
            query += """ AND a.id %s IN (SELECT id
                                         FROM fact_index
                                         WHERE fact_index MATCH '%s')""" % ('NOT' if reverse_search_terms else '',
                                                                            search_terms)

        query += " ORDER BY a.start_time, e.name"

        facts = self.fetchall(query, (self._unsorted_localized,
                                      datetime_from,
                                      datetime_to))

        #first let's put all tags in an array
        facts = self.__group_tags(facts)

        res = []
        for fact in facts:
            # heuristics to assign tasks to proper days

            # if fact has no end time, set the last minute of the day,
            # or current time if fact has happened in last 12 hours
            if fact["end_time"]:
                fact_end_time = fact["end_time"]
            elif (dt.datetime.now().date() == fact["start_time"].date()) or \
                 (dt.datetime.now() - fact["start_time"]) <= dt.timedelta(hours=12):
                fact_end_time = dt.datetime.now().replace(microsecond = 0)
            else:
                fact_end_time = fact["start_time"]

            fact_start_date = fact["start_time"].date() \
                - dt.timedelta(1 if fact["start_time"].time() < split_time else 0)
            fact_end_date = fact_end_time.date() \
                - dt.timedelta(1 if fact_end_time.time() < split_time else 0)
            fact_date_span = fact_end_date - fact_start_date

            # check if the task spans across two dates
            if fact_date_span.days == 1:
                datetime_split = dt.datetime.combine(fact_end_date, split_time)
                start_date_duration = datetime_split - fact["start_time"]
                end_date_duration = fact_end_time - datetime_split
                if start_date_duration > end_date_duration:
                    # most of the task was done during the previous day
                    fact_date = fact_start_date
                else:
                    fact_date = fact_end_date
            else:
                # either doesn't span or more than 24 hrs tracked
                # (in which case we give up)
                fact_date = fact_start_date

            if fact_date < date or fact_date > end_date:
                # due to spanning we've jumped outside of given period
                continue

            fact["date"] = fact_date
            fact["delta"] = fact_end_time - fact["start_time"]
            res.append(fact)

        return res

    def __remove_fact(self, fact_id):
        statements = ["DELETE FROM fact_tags where fact_id = ?",
                      "DELETE FROM facts where id = ?"]
        self.execute(statements, [(fact_id,)] * 2)

        self.__remove_index([fact_id])

    def __get_category_activities(self, category_id):
        """returns list of activities, if category is specified, order by name
           otherwise - by activity_order"""
        query = """
                   SELECT a.id, a.name, a.category_id, b.name as category
                     FROM activities a
                LEFT JOIN categories b on coalesce(b.id, -1) = a.category_id
                    WHERE category_id = ?
                      AND deleted is null
                 ORDER BY lower(a.name)
        """

        return self.fetchall(query, (category_id, ))


    def __get_activities(self, search):
        """returns list of activities for autocomplete,
           activity names converted to lowercase"""

        query = """
                   SELECT a.name AS name, b.name AS category
                     FROM activities a
                LEFT JOIN categories b ON coalesce(b.id, -1) = a.category_id
                LEFT JOIN facts f ON a.id = f.activity_id
                    WHERE deleted IS NULL
                      AND a.search_name LIKE ? ESCAPE '\\'
                 GROUP BY a.id
                 ORDER BY max(f.start_time) DESC, lower(a.name)
                    LIMIT 50
        """
        search = search.lower()
        search = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        activities = self.fetchall(query, (u'%s%%' % search, ))

        return activities

    def __remove_activity(self, id):
        """ check if we have any facts with this activity and behave accordingly
            if there are facts - sets activity to deleted = True
            else, just remove it"""

        query = "select count(*) as count from facts where activity_id = ?"
        bound_facts = self.fetchone(query, (id,))['count']

        if bound_facts > 0:
            self.execute("UPDATE activities SET deleted = 1 WHERE id = ?", (id,))
        else:
            self.execute("delete from activities where id = ?", (id,))

        # Finished! - deleted an activity with more than 50 facts on it
        if trophies and bound_facts >= 50:
            trophies.unlock("finished")

    def __remove_category(self, id):
        """move all activities to unsorted and remove category"""

        affected_query = """
            SELECT id
              FROM facts
             WHERE activity_id in (SELECT id FROM activities where category_id=?)
        """
        affected_ids = [res[0] for res in self.fetchall(affected_query, (id,))]

        update = "update activities set category_id = -1 where category_id = ?"
        self.execute(update, (id, ))

        self.execute("delete from categories where id = ?", (id, ))

        self.__remove_index(affected_ids)


    def __add_activity(self, name, category_id = None, temporary = False):
        # first check that we don't have anything like that yet
        activity = self.__get_activity_by_name(name, category_id)
        if activity:
            return activity['id']

        #now do the create bit
        category_id = category_id or -1

        deleted = None
        if temporary:
            deleted = 1


        query = """
                   INSERT INTO activities (name, search_name, category_id, deleted)
                        VALUES (?, ?, ?, ?)
        """
        self.execute(query, (name, name.lower(), category_id, deleted))
        return self.__last_insert_rowid()

    def __remove_index(self, ids):
        """remove affected ids from the index"""
        if not ids:
            return

        ids = ",".join((str(id) for id in ids))
        self.execute("DELETE FROM fact_index where id in (%s)" % ids)


    def __check_index(self, start_date, end_date):
        """check if maybe index needs rebuilding in the time span"""
        index_query = """SELECT id
                           FROM facts
                          WHERE (end_time >= ? OR end_time IS NULL)
                            AND start_time <= ?
                            AND id not in(select id from fact_index)"""

        rebuild_ids = ",".join([str(res[0]) for res in self.fetchall(index_query, (start_date, end_date))])

        if rebuild_ids:
            query = """
                       SELECT a.id AS id,
                              a.start_time AS start_time,
                              a.end_time AS end_time,
                              a.description as description,
                              b.name AS name, b.id as activity_id,
                              coalesce(c.name, ?) as category,
                              e.name as tag
                         FROM facts a
                    LEFT JOIN activities b ON a.activity_id = b.id
                    LEFT JOIN categories c ON b.category_id = c.id
                    LEFT JOIN fact_tags d ON d.fact_id = a.id
                    LEFT JOIN tags e ON e.id = d.tag_id
                        WHERE a.id in (%s)
                     ORDER BY a.id
            """ % rebuild_ids

            facts = self.__group_tags(self.fetchall(query, (self._unsorted_localized, )))

            insert = """INSERT INTO fact_index (id, name, category, description, tag)
                             VALUES (?, ?, ?, ?, ?)"""
            params = [(fact['id'], fact['name'], fact['category'], fact['description'], " ".join(fact['tags'])) for fact in facts]

            self.executemany(insert, params)


    """ Here be dragons (lame connection/cursor wrappers) """
    def get_connection(self):
        if self.con is None:
            self.con = sqlite.connect(self.db_path, detect_types=sqlite.PARSE_DECLTYPES|sqlite.PARSE_COLNAMES)
            self.con.row_factory = sqlite.Row

        return self.con

    connection = property(get_connection, None)

    def fetchall(self, query, params = None):
        con = self.connection
        cur = con.cursor()

        logging.debug("%s %s" % (query, params))

        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

        res = cur.fetchall()
        cur.close()

        return res

    def fetchone(self, query, params = None):
        res = self.fetchall(query, params)
        if res:
            return res[0]
        else:
            return None

    def execute(self, statement, params = ()):
        """
        execute sql statement. optionally you can give multiple statements
        to save on cursor creation and closure
        """
        con = self.__con or self.connection
        cur = self.__cur or con.cursor()

        if isinstance(statement, list) == False: # we expect to receive instructions in list
            statement = [statement]
            params = [params]

        for state, param in zip(statement, params):
            logging.debug("%s %s" % (state, param))
            cur.execute(state, param)

        if not self.__con:
            con.commit()
            cur.close()
            self.register_modification()

    def executemany(self, statement, params = []):
        con = self.__con or self.connection
        cur = self.__cur or con.cursor()

        logging.debug("%s %s" % (statement, params))
        cur.executemany(statement, params)

        if not self.__con:
            con.commit()
            cur.close()
            self.register_modification()



    def start_transaction(self):
        # will give some hints to execute not to close or commit anything
        self.__con = self.connection
        self.__cur = self.__con.cursor()

    def end_transaction(self):
        self.__con.commit()
        self.__cur.close()
        self.__con, self.__cur = None, None
        self.register_modification()

    def run_fixtures(self):
        self.start_transaction()

        """upgrade DB to hamster version"""
        version = self.fetchone("SELECT version FROM version")["version"]
        current_version = 9

        if version < 8:
            # working around sqlite's utf-f case sensitivity (bug 624438)
            # more info: http://www.gsak.net/help/hs23820.htm
            self.execute("ALTER TABLE activities ADD COLUMN search_name varchar2")

            activities = self.fetchall("select * from activities")
            statement = "update activities set search_name = ? where id = ?"
            for activity in activities:
                self.execute(statement, (activity['name'].lower(), activity['id']))

            # same for categories
            self.execute("ALTER TABLE categories ADD COLUMN search_name varchar2")
            categories = self.fetchall("select * from categories")
            statement = "update categories set search_name = ? where id = ?"
            for category in categories:
                self.execute(statement, (category['name'].lower(), category['id']))

        if version < 9:
            # adding full text search
            self.execute("""CREATE VIRTUAL TABLE fact_index
                                           USING fts3(id, name, category, description, tag)""")


        # at the happy end, update version number
        if version < current_version:
            #lock down current version
            self.execute("UPDATE version SET version = %d" % current_version)
            print "updated database from version %d to %d" % (version, current_version)

            # oldtimer – database version structure had been performed on startup (thus we know that user has been on at least 2 versions)
            if trophies:
                trophies.unlock("oldtimer")

        self.end_transaction()
