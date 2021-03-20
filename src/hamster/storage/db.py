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
logger = logging.getLogger(__name__)   # noqa: E402

import os, time
import itertools
import sqlite3 as sqlite
from shutil import copy as copyfile
try:
    from gi.repository import Gio as gio
except ImportError:
    print("Could not import gio - requires pygobject. File monitoring will be disabled")
    gio = None

import hamster
from hamster.lib import datetime as dt
from hamster.external.external import ExternalSource
from hamster.lib.configuration import conf
from hamster.lib.fact import Fact
from hamster.storage import storage


# note: "zero id means failure" is quite standard,
#       and that kind of convention will be mandatory for the dbus interface
#       (None cannot pass through an integer signature).

class Storage(storage.Storage):
    con = None # Connection will be created on demand
    external = None
    external_need_update = False
    def __init__(self, unsorted_localized="Unsorted", database_dir=None):
        """Database storage.

        Args:
            unsorted_localized (str):
                Default Fact.category value for returned facts
                that were without any category in the db.
                This is kept mainly for compatibility reasons.
                The recommended value is an empty string.
                How to handle empty category is now left to the caller.
            database_dir (path):
                Directory holding the database file,
                or None to use the default location.

        Note: Zero id means failure.
              Unsorted category id is hard-coded as -1
        """
        storage.Storage.__init__(self)

        self._unsorted_localized = unsorted_localized

        self.__con = None
        self.__cur = None
        self.__last_etag = None


        self.db_path = self.__init_db_file(database_dir)
        logger.info("database: '{}'".format(self.db_path))

        if gio:
            # add file monitoring so the app does not have to be restarted
            # when db file is rewritten
            def on_db_file_change(monitor, gio_file, event_uri, event):
                logger.debug(event)
                if event == gio.FileMonitorEvent.CHANGES_DONE_HINT:
                    if gio_file.query_info(gio.FILE_ATTRIBUTE_ETAG_VALUE,
                                           gio.FileQueryInfoFlags.NONE,
                                           None).get_etag() == self.__last_etag:
                        # ours
                        logger.info("database updated")
                        return
                elif event == gio.FileMonitorEvent.DELETED:
                    self.con = None

                if event == gio.FileMonitorEvent.CHANGES_DONE_HINT:
                    logger.warning("DB file has been modified externally. Calling all stations")
                    self.dispatch_overwrite()

            self.__database_file = gio.File.new_for_path(self.db_path)
            self.__db_monitor = self.__database_file.monitor_file(gio.FileMonitorFlags.WATCH_MOUNTS, None)
            self.__db_monitor.connect("changed", on_db_file_change)

        self.run_fixtures()

        self.external = ExternalSource(conf)

    def __init_db_file(self, database_dir):
        if not database_dir:
            try:
                from xdg.BaseDirectory import xdg_data_home
            except ImportError:
                xdg_data_home = os.environ.get('XDG_DATA_HOME')
                if not xdg_data_home:
                    xdg_data_home = os.path.join(os.path.expanduser('~'), '.local', 'share')
                    logger.warning("No xdg_data_home - assuming ~/.local/share")
            database_dir = os.path.join(xdg_data_home, 'hamster')

        if not os.path.exists(database_dir):
            os.makedirs(database_dir, 0o744)

        db_path = os.path.join(database_dir, "hamster.db")

        # check if we have a database at all
        if not os.path.exists(db_path):
            # handle pre-existing hamster-applet database
            # try most recent directories first
            # change from hamster-applet to hamster-time-tracker:
            # 9f345e5e (2019-09-19)
            old_dirs = ['hamster-time-tracker', 'hamster-applet']
            for old_dir in old_dirs:
                old_db_path = os.path.join(xdg_data_home, old_dir, 'hamster.db')
                if os.path.exists(old_db_path):
                    logger.warning("Linking {} with {}".format(old_db_path, db_path))
                    os.link(old_db_path, db_path)
                    break
            if not os.path.exists(db_path):
                # make a copy of the empty template hamster.db
                if hamster.installed:
                    from hamster import defs  # only available when running installed
                    data_dir = os.path.join(defs.DATA_DIR, "hamster")
                else:
                    # running from sources
                    module_dir = os.path.dirname(os.path.realpath(__file__))
                    if os.path.exists(os.path.join(module_dir, "data")):
                        # running as flask app. XXX - detangle
                        data_dir = os.path.join(module_dir, "data")
                    else:
                        # get ./data from ./src/hamster/storage/db.py (3 levels up)
                        data_dir = os.path.join(module_dir, '..', '..', '..', 'data')
                logger.warning("Database not found in {} - installing default from {}!"
                               .format(db_path, data_dir))
                copyfile(os.path.join(data_dir, 'hamster.db'), db_path)

            #change also permissions - sometimes they are 444
            os.chmod(db_path, 0o664)

        db_path = os.path.realpath(db_path)  # needed for file monitoring?

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
        set_complete = [str(tag["id"]) for tag in db_tags if tag["autocomplete"] in (0, "false")]
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
        to_uncomplete = [str(tag["id"]) for tag in gone
                         if tag["occurences"] > 0 and tag["autocomplete"] in (1, "true")]

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
        """Change the category of an activity.

        If an activity already exists with the same name
        in the target category,
        make all relevant facts use this target activity.

        Args:
            id (int): id of the source activity
            category_id (int): id of the target category
        Returns:
            boolean: whether the database was changed.
        """
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
        """Get most recent, preferably not deleted activity by it's name.
        If category_id is None or 0, show all activities matching name.
        Otherwise, filter on the specified category.
        """

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
        """Return category id from its name.

        0 means none found.
        """
        if not name:
            # Unsorted
            return -1

        query = """
                   SELECT id from categories
                    WHERE lower(name) = lower(?)
                 ORDER BY id desc
                    LIMIT 1
        """

        res = self.fetchone(query, (name, ))

        if res:
            return res['id']

        return 0

    def _dbfact_to_libfact(self, db_fact):
        """Convert a db fact (coming from __group_facts) to Fact."""
        return Fact(activity=db_fact["name"],
                    category=db_fact["category"],
                    description=db_fact["description"],
                    tags=db_fact["tags"],
                    start_time=db_fact["start_time"],
                    end_time=db_fact["end_time"],
                    id=db_fact["id"],
                    exported=db_fact["exported"],
                    activity_id=db_fact["activity_id"])

    def __get_fact(self, id):
        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS name, b.id as activity_id,
                          coalesce(c.name, ?) as category, coalesce(c.id, -1) as category_id,
                          e.name as tag,
                          a.exported AS exported
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                LEFT JOIN categories c ON b.category_id = c.id
                LEFT JOIN fact_tags d ON d.fact_id = a.id
                LEFT JOIN tags e ON e.id = d.tag_id
                    WHERE a.id = ?
                 ORDER BY e.name
        """

        fact_rows = self.fetchall(query, (self._unsorted_localized, id))
        assert len(fact_rows) > 0, "No fact with id {}".format(id)
        dbfact = self.__group_tags(fact_rows)[0]
        fact = self._dbfact_to_libfact(dbfact)
        logger.info("got fact {}".format(fact))
        return fact

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
                    "activity_id", "category", "tag", "exported"]
            grouped_fact = dict([(key, grouped_fact[key]) for key in keys])

            grouped_fact["tags"] = [ft["tag"] for ft in fact_tags if ft["tag"]]
            grouped_facts.append(grouped_fact)
        return grouped_facts


    def __touch_fact(self, fact, end_time = None):
        end_time = end_time or dt.datetime.now()
        # tasks under one minute do not count
        if end_time - fact.start_time < dt.timedelta(minutes = 1):
            self.__remove_fact(fact.id)
        else:
            query = """
                       UPDATE facts
                          SET end_time = ?
                        WHERE id = ?
            """
            self.execute(query, (end_time, fact.id))

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
        #TODO gso: end_time and start_time round

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
            if fact["start_time"] is None:
                continue

            # fact is a sqlite.Row, indexable by column name
            # handle case with not finished activities
            fact_end_time = fact["end_time"] or dt.datetime.now()

            # won't eliminate as it is better to have overlapping entries than loosing data
            if start_time < fact["start_time"] and end_time >= fact_end_time:
                continue

            # split - truncate until beginning of new entry and create new activity for end
            if fact["start_time"] < start_time < fact_end_time and \
               fact["start_time"] < end_time <= fact_end_time:

                logger.info("splitting %s" % fact["name"])
                # truncate until beginning of the new entry
                self.execute("""UPDATE facts
                                   SET end_time = ?
                                 WHERE id = ?""", (start_time, fact["id"]))
                fact_name = fact["name"]

                # TODO gso: move changes from master

                # create new fact for the end
                new_fact = Fact(activity=fact["name"],
                                category=fact["category"],
                                description=fact["description"],
                                start_time=end_time,
                                end_time=fact_end_time)
                storage.Storage.check_fact(new_fact)
                new_fact_id = self.__add_fact(new_fact)

                # copy tags
                tag_update = """INSERT INTO fact_tags(fact_id, tag_id)
                                     SELECT ?, tag_id
                                       FROM fact_tags
                                      WHERE fact_id = ?"""
                self.execute(tag_update, (new_fact_id, fact["id"])) #clone tags

            # overlap start
            elif start_time <= fact["start_time"] <= end_time:
                logger.info("Overlapping start of %s" % fact["name"])
                self.execute("UPDATE facts SET start_time=? WHERE id=?",
                             (end_time, fact["id"]))

            # overlap end
            elif start_time < fact_end_time <= end_time:
                logger.info("Overlapping end of %s" % fact["name"])
                self.execute("UPDATE facts SET end_time=? WHERE id=?",
                             (start_time, fact["id"]))


    def __add_fact(self, fact, temporary=False):
        """Add fact to database.

        Args:
            fact (Fact)
        Returns:
            int, the new fact id in the database (> 0) on success,
                 0 if nothing needed to be done
                 (e.g. if the same fact was already on-going),
                 note: a sanity check on the given fact is performed first,
                       that would raise an AssertionError.
                       Other errors would also be handled through exceptions.
        """
        logger.info("adding fact {}".format(fact))

        start_time = fact.start_time
        end_time = fact.end_time

        # get tags from database - this will create any missing tags too
        tags = [(tag['id'], tag['name'], tag['autocomplete']) for tag in self.get_tag_ids(fact.tags)]

        # now check if maybe there is also a category
        category_id = self.__get_category_id(fact.category)
        if not category_id:
            category_id = self.__add_category(fact.category)

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
            if facts and facts[-1].end_time is None:
                previous = facts[-1]

            if previous and previous.start_time <= start_time:
                # check if maybe that is the same one, in that case no need to restart
                if (previous.activity_id == activity_id
                    and set(previous.tags) == set([tag[1] for tag in tags])
                    and (previous.description or "") == (fact.description or "")
                   ):
                    logger.info("same fact, already on-going, nothing to do")
                    return 0

                # if no description is added
                # see if maybe previous was too short to qualify as an activity
                if (not previous.description
                    and 60 >= (start_time - previous.start_time).seconds >= 0
                   ):
                    self.__remove_fact(previous.id)

                    # now that we removed the previous one, see if maybe the one
                    # before that is actually same as the one we want to start
                    # (glueing)
                    if len(facts) > 1 and 60 >= (start_time - facts[-2].end_time).seconds >= 0:
                        before = facts[-2]
                        if (before.activity_id == activity_id
                            and set(before.tags) == set([tag[1] for tag in tags])
                           ):
                            # resume and return
                            update = """
                                       UPDATE facts
                                          SET end_time = null
                                        WHERE id = ?
                            """
                            self.execute(update, (before.id,))

                            return before.id
                else:
                    # otherwise stop
                    update = """
                               UPDATE facts
                                  SET end_time = ?
                                WHERE id = ?
                    """
                    self.execute(update, (start_time, previous.id))


        # done with the current activity, now we can solve overlaps
        if not end_time:
            end_time = self.__squeeze_in(start_time)
        else:
            self.__solve_overlaps(start_time, end_time)


        # finally add the new entry
        insert = """
                    INSERT INTO facts (activity_id, start_time, end_time, description, exported)
                               VALUES (?, ?, ?, ?, ?)
        """
        self.execute(insert, (activity_id, start_time, end_time, fact.description, fact.exported))

        fact_id = self.__last_insert_rowid()

        #now link tags
        insert = ["insert into fact_tags(fact_id, tag_id) values(?, ?)"] * len(tags)
        params = [(fact_id, tag[0]) for tag in tags]
        self.execute(insert, params)

        self.__remove_index([fact_id])
        logger.info("fact successfully added, with id #{}".format(fact_id))
        return fact_id

    def __last_insert_rowid(self):
        return self.fetchone("SELECT last_insert_rowid();")[0] or 0


    def __get_todays_facts(self):
        return self.__get_facts(dt.Range.today())

    def __get_facts(self, range, search_terms="", limit = 0, asc_by_date = True):
        datetime_from = range.start
        datetime_to = range.end

        logger.info("searching for facts from {} to {}".format(datetime_from, datetime_to))

        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS name, b.id as activity_id,
                          coalesce(c.name, ?) as category,
                          e.name as tag,
                          a.exported as exported
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
            # TODO gso: add NOT operator
            query += """ AND a.id %s IN (SELECT id
                                         FROM fact_index
                                         WHERE fact_index MATCH '%s')""" % ('NOT' if reverse_search_terms else '',
                                                                            search_terms)

        if asc_by_date:
            query += " ORDER BY a.start_time, e.name"
        else:
            query += " ORDER BY a.start_time desc, e.name"

        if limit and limit > 0:
            query += " LIMIT " + str(limit)

        fact_rows = self.fetchall(query, (self._unsorted_localized,
                                          datetime_from,
                                          datetime_to))
        #first let's put all tags in an array
        dbfacts = self.__group_tags(fact_rows)
        # ignore old on-going facts
        return [self._dbfact_to_libfact(dbfact) for dbfact in dbfacts
                if dbfact["start_time"] >= datetime_from - dt.timedelta(days=30)]

    def __remove_fact(self, fact_id):
        logger.info("removing fact #{}".format(fact_id))
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


    def __get_ext_activities(self, search):
        return self.get_external().get_activities(search)

    def __export_fact(self, fact_id) -> bool:
        fact = self.get_fact(fact_id)
        return self.get_external().export(fact)

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
        activities = self.fetchall(query, ('%s%%' % search, ))

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
        logger.info("removing fact #{} from index".format(ids))
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
                              e.name as tag,
                              a.exported AS exported
                         FROM facts a
                    LEFT JOIN activities b ON a.activity_id = b.id
                    LEFT JOIN categories c ON b.category_id = c.id
                    LEFT JOIN fact_tags d ON d.fact_id = a.id
                    LEFT JOIN tags e ON e.id = d.tag_id
                        WHERE a.id in (%s)
                     ORDER BY a.id
            """ % rebuild_ids

            dbfacts = self.__group_tags(self.fetchall(query, (self._unsorted_localized, )))
            facts = [self._dbfact_to_libfact(dbfact) for dbfact in dbfacts]

            insert = """INSERT INTO fact_index (id, name, category, description, tag)
                             VALUES (?, ?, ?, ?, ?)"""
            params = [(fact.id, fact.activity, fact.category, fact.description, " ".join(fact.tags)) for fact in facts]

            self.executemany(insert, params)

    """ Here be dragons (lame connection/cursor wrappers) """
    def get_connection(self):
        if self.con is None:
            self.con = sqlite.connect(self.db_path, detect_types=sqlite.PARSE_DECLTYPES|sqlite.PARSE_COLNAMES)
            self.con.row_factory = sqlite.Row

        return self.con

    connection = property(get_connection, None)

    def fetchall(self, query, params = None):
        """Execute query.

        Returns:
            list(sqlite.Row)
        """
        con = self.connection
        cur = con.cursor()

        logger.debug("%s %s" % (query, params))

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
            logger.debug("%s %s" % (state, param))
            cur.execute(state, param)

        if not self.__con:
            con.commit()
            cur.close()
            self.register_modification()

    def executemany(self, statement, params = []):
        con = self.__con or self.connection
        cur = self.__cur or con.cursor()

        logger.debug("%s %s" % (statement, params))
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
        current_version = 10

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
        if version < 10:
            # adding exported
            self.execute("""ALTER TABLE facts ADD COLUMN exported bool default false""")
            self.execute("""UPDATE facts set exported=1""")


        # at the happy end, update version number
        if version < current_version:
            #lock down current version
            self.execute("UPDATE version SET version = %d" % current_version)
            print("updated database from version %d to %d" % (version, current_version))

        self.end_transaction()

    def get_external(self):
        if self.external_need_update:
            self.refresh_external(conf)
        return self.external

    def refresh_external(self, conf):
        self.external = ExternalSource(conf)
        self.external_need_update = False


# datetime/sql conversions

DATETIME_LOCAL_FMT = "%Y-%m-%d %H:%M:%S"


def adapt_datetime(t):
    """Convert datetime t to the suitable sql representation."""
    return t.isoformat(" ")


def convert_datetime(s):
    """Convert the sql timestamp to datetime.

    s is in bytes.
    """

    # convert s from bytes to utf-8, and keep only data up to seconds
    # 10 chars for YYYY-MM-DD, 1 space, 8 chars for HH:MM:SS
    # note: let's leave any further rounding to dt.datetime.
    datetime_string = s.decode('utf-8')[0:19]

    return dt.datetime.strptime(datetime_string, DATETIME_LOCAL_FMT)


sqlite.register_adapter(dt.datetime, adapt_datetime)
sqlite.register_converter("timestamp", convert_datetime)
