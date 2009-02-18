# - coding: utf-8 -

# Copyright (C) 2007, 2008 Toms Bauģis <toms.baugis at gmail.com>
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

try:
    import sqlite3 as sqlite
except ImportError:
    try:
        from pysqlite2 import dbapi2 as sqlite
    except ImportError:
        print "Error: Neither sqlite3 nor pysqlite2 found"
        raise
import os, time
import datetime
import hamster
import hamster.storage
import datetime as dt
import copy
        
class Storage(hamster.storage.Storage):
    # we are saving data under $HOME/.gnome2/hamster-applet/hamster.db
    con = None # Connection will be created on demand

    def __get_category_list(self):
        return self.fetchall("SELECT * FROM categories ORDER BY category_order")

    def __change_category(self, id, category_id):
        # first check if we don't have an activity with same name before us
        activity = self.fetchone("select name from activities where id = ?", (id, ))
        existing_id = self.__get_activity_by_name(activity['name'], category_id)
        
        if id == existing_id: # we are already there, go home
            return False
        
        if existing_id: #ooh, we have something here!
            # first move all facts that belong to movable activity to the new one
            update = """
                       UPDATE facts
                          SET activity_id = ?
                        WHERE activity_id = ?
            """
            
            self.execute(update, (existing_id, id))
            
            # and now get rid of our friend
            self.__remove_activity(id)
        
        else: #just moving        
            query = "SELECT max(activity_order) + 1 FROM activities WHERE category_id = ?"
            max_order = self.fetchone(query, (category_id, ))[0] or 1
            
            statement = """
                       UPDATE activities 
                          SET category_id = ?, activity_order = ?
                        WHERE id = ?
            """
            
            self.execute(statement, (category_id, max_order, id))
        
        return True
    
    def __add_category(self, name):
        new_rec = self.fetchone("select max(id) +1, max(category_order) + 1  from categories")

        id, order = new_rec[0] or 1, new_rec[1] or 1

        query = """
                   INSERT INTO categories (id, name, category_order)
                        VALUES (?, ?, ?)
        """
        self.execute(query, (id, name, order))
        return id

    def __update_category(self, id,  name):
        if id > -1: # Update, and ignore unsorted, if that was somehow triggered
            update = """
                       UPDATE categories
                           SET name = ?
                         WHERE id = ?
            """
            self.execute(update, (name, id))        
        
    def __move_activity(self, source_id, target_order, insert_after = True):
        statement = "UPDATE activities SET activity_order = activity_order + 1"
        
        if insert_after:
            statement += " WHERE activity_order > ?"
        else:
            statement += " WHERE activity_order >= ?"

        self.execute(statement, (target_order, ))
        
        statement = "UPDATE activities SET activity_order = ? WHERE id = ?"
        
        if insert_after:
            self.execute(statement, (target_order + 1, source_id))
        else:
            self.execute(statement, (target_order, source_id))
            
        
        
    def __get_activity_by_name(self, name, category_id = None):
        """get most recent, preferably not deleted activity by it's name"""
        
        if category_id:
            query = """
                       SELECT id, deleted from activities 
                        WHERE lower(name) = lower(?)
                          AND category_id = ?
                     ORDER BY deleted, id desc
                        LIMIT 1
            """
            
            res = self.fetchone(query, (name, category_id))
        else:
            query = """
                       SELECT id, deleted from activities 
                        WHERE lower(name) = lower(?)
                     ORDER BY deleted, id desc
                        LIMIT 1
            """

            res = self.fetchone(query, (name, ))
        
        if res:
            # if the activity was marked as deleted, ressurect on first call
            # and put in the unsorted category
            if res['deleted']:
                update = """
                            UPDATE activities
                               SET deleted = null, category_id = -1
                             WHERE id = ?
                        """
                self.execute(update, (res['id'], ))
            
            return res['id']
        
        return None

    def __get_category_by_name(self, name):
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
        query = """SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS name, b.id as activity_id
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                    WHERE a.id = ? 
        """
        return self.fetchone(query, (id, ))

    def __get_last_activity(self):
        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS name, b.id as activity_id
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                    WHERE date(a.start_time) = ?
                 ORDER BY a.start_time desc
                    LIMIT 1
        """
        return self.fetchone(query, (dt.date.today(), ))

    def __touch_fact(self, fact, end_time):
        # tasks under one minute do not count
        if end_time - fact['start_time'] < datetime.timedelta(minutes = 1):
            self.__remove_fact(fact['id'])
        else:
            query = """
                       UPDATE facts
                          SET end_time = ?
                        WHERE id = ?
            """
            self.execute(query, (end_time, fact['id']))

    def __add_fact(self, activity_name, start_time = None, end_time = None):
        start_time = start_time or datetime.datetime.now()
        
        #see if we have description of activity somewhere here (delimited by comma)
        description = None
        if activity_name.find(",") > 0:
            activity_name, description = activity_name.split(",", 1)
            description = description.strip()
        
        # now check if maybe there is also a category
        category_id = None
        if activity_name.find("@") > 0:
            #at symbol marks category
            activity_name, category_name = activity_name.split("@", 1)
            
            if category_name:
                category_name = category_name.strip()
                category_id = self.__get_category_by_name(category_name)
                if not category_id:
                    category_id = self.__add_category(category_name)
        
        # try to find activity
        activity_id = self.__get_activity_by_name(activity_name, category_id)

        if not activity_id:
            activity_id = self.__add_activity(activity_name, category_id)


        # now fetch facts for the specified day and check if we have to
        # split or change span 
        day_facts = self.__get_facts(start_time.date())
        for fact in day_facts:
            # first check if maybe we are overlapping end
            if fact['end_time'] and fact['start_time'] < start_time < fact['end_time']:
                #set fact's end time to our start one
                update = """
                           UPDATE facts
                              SET end_time = ?
                            WHERE id = ?
                """
                self.execute(update, (start_time, fact["id"]))

                # now check - maybe we are inside the fact. in that case
                # we should create another task after our one
                if end_time and end_time < fact['end_time']:
                    self.__add_fact(fact['name'], end_time, fact['end_time'])

           
            else: #end's fine? what about start then?
                if fact['end_time'] and end_time and fact['start_time'] < end_time < fact['end_time'] \
                or not fact['end_time'] and end_time and fact['start_time'] < end_time: # case for the entry before the last one
                    #set fact's start time to our end one
                    update = """
                               UPDATE facts
                                  SET start_time = ?
                                WHERE id = ?
                    """
                    self.execute(update, (end_time, fact["id"]))

        # now check if maybe we are at the last task, and if that's true
        # look if we maybe have to finish it or delete if it was too short
        if day_facts:
            last_fact = day_facts[-1]
            
            if last_fact['end_time'] == None and last_fact['start_time'] < start_time:
                #if this is the same, ongoing activity, then there is no need to create another one
                if last_fact['activity_id'] == activity_id:
                    return last_fact
                
                
                delta = (start_time - last_fact['start_time'])
            
                if 60 >= delta.seconds >= 0:
                    self.__remove_fact(last_fact['id'])
                    start_time = last_fact['start_time']

                    # go further now and check, maybe task before the last one
                    # is the same we have now. If that happened before less
                    # than a minute - remove end time!
                    if len(day_facts) > 2 and day_facts[-2]['name'] == activity_name:
                        print day_facts[-2]['name'], activity_name, day_facts[-2]['end_time'], start_time
                        delta = (start_time - day_facts[-2]['end_time'])
                        if 60 >= delta.seconds >= 0:
                            update = """
                                        UPDATE facts
                                           SET end_time = null
                                         WHERE id = ?
                                    """
                            self.execute(update, (day_facts[-2]["id"],))
                            return day_facts[-2]
                else:
                    #set previous fact end time
                    update = """
                               UPDATE facts
                                  SET end_time = ?
                                WHERE id = ?
                    """
                    self.execute(update, (start_time, fact["id"]))


        # finally add the new entry
        insert = """
                    INSERT INTO facts (activity_id, start_time, end_time, description)
                               VALUES (?, ?, ?, ?)
        """
        self.execute(insert, (activity_id, start_time, end_time, description))

        fact_id = self.fetchone("select max(id) as max_id from facts")['max_id']
        
        return self.__get_fact(fact_id)


    def __get_facts(self, date, end_date = None):
        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS name, b.id as activity_id,
                          coalesce(c.name, ?) as category, coalesce(c.id, -1) as category_id
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                LEFT JOIN categories c on b.category_id = c.id
                    WHERE date(a.start_time) >= ? and date(a.start_time) <= ?
                       OR date(a.end_time) >= ? and date(a.end_time) <= ?
                 ORDER BY a.start_time
        """
        end_date = end_date or date
        
        facts = self.fetchall(query, (_("Unsorted"), date, end_date, date, end_date))
        res = []


        for fact in facts:
            
            start_date = fact["start_time"].date()
            if fact["end_time"]:
                end_date = fact["end_time"].date()
            else:
                end_date = None
                                   
            f = dict(
                id = fact["id"],
                start_time = fact["start_time"],
                end_time = fact["end_time"],
                description = fact["description"],
                name = fact["name"],
                activity_id = fact["activity_id"],
                category = fact["category"],
                category_id = fact["category_id"]
            )
            
            
            if not end_date or start_date == end_date:
                if end_date:
                    f["delta"] = fact["end_time"] - fact["start_time"]
                elif start_date == dt.date.today() \
                          and fact["start_time"] < dt.datetime.now():
                    f["delta"] = dt.datetime.now() -  fact["start_time"]
                else:
                    f["delta"] = None

                res.append(f)
            else:
                #if start and end dates do not much, let's populate two entries!
                if date <= f["start_time"].date()  <= end_date:
                    start_fact = copy.copy(f)
                    start_fact["end_time"] = dt.datetime.combine(start_fact["start_time"], dt.time(23, 59))
                    start_fact["delta"] = start_fact["end_time"] - start_fact["start_time"]
                    res.append(start_fact)

                if date <= fact["end_time"].date()  <= end_date:
                    end_fact = copy.copy(f)
                    end_fact["start_time"] = dt.datetime.combine(end_fact["end_time"], dt.time(0, 0))
                    end_fact["delta"] = end_fact["end_time"] - end_fact["start_time"]
                    res.append(end_fact)
        return res

    def __get_popular_categories(self):
        """returns categories used in the specified interval"""
        query = """
                   SELECT coalesce(c.name, ?) as category, count(a.id) as popularity
                     FROM facts a
                LEFT JOIN activities b on a.activity_id = b.id
                LEFT JOIN categories c on c.id = b.category_id
                 GROUP BY b.category_id
                 ORDER BY popularity desc
        """
        return self.fetchall(query, (_("Unsorted"), ))

    def __get_interval_activity_ids(self, date, end_date = None):
        """returns activities used in the specified interval"""
        query = """
                   SELECT a.name, coalesce(b.name, ?) as category_name
                     FROM activities a
                LEFT JOIN categories b on b.id = a.category_id
                    WHERE a.id in (SELECT activity_id from facts
                                  WHERE date(start_time) >= ?
                                    AND date(start_time) <= ?)
        """
        end_date = end_date or date        

        return self.fetchall(query, (_("Unsorted"), date, end_date))
        
    
    def __remove_fact(self, fact_id):
        query = """
                   DELETE FROM facts
                         WHERE id = ?
        """
        self.execute(query, (fact_id,))

    def __get_activities(self, category_id = None):
        """returns list of activities, if category is specified, order by name
           otherwise - by activity_order"""
        if category_id:
            query = """
                       SELECT a.*, b.name as category
                         FROM activities a
                    LEFT JOIN categories b on coalesce(b.id, -1) = a.category_id
                        WHERE category_id = ?
                          AND deleted is null
            """
            
            # unsorted entries we sort by name - others by ID
            if category_id == -1:
                query += "ORDER BY lower(a.name)"
            else:
                query += "ORDER BY a.activity_order"
                
            activities = self.fetchall(query, (category_id, ))
            
        else:
            query = """
                       SELECT a.*, b.name as category
                         FROM activities a
                    LEFT JOIN categories b on coalesce(b.id, -1) = a.category_id
                        WHERE deleted is null
                     ORDER BY lower(a.name)
            """
            activities = self.fetchall(query)
            
        return activities

    def __get_sorted_activities(self):
        """returns list of acitivities that have categories"""
        query = """
                   SELECT a.*, b.name as category, b.category_order
                     FROM activities a
                LEFT JOIN categories b on coalesce(b.id, -1) = a.category_id
                    WHERE a.category_id > -1
                      AND a.deleted is null
                 ORDER BY category_order, activity_order
        """
        return self.fetchall(query)
        
    def __get_autocomplete_activities(self):
        """returns list of activities for autocomplete,
           activity names converted to lowercase"""

        query = """
                   SELECT lower(a.name) as name, b.name as category
                     FROM activities a
                LEFT JOIN categories b on coalesce(b.id, -1) = a.category_id
                    WHERE deleted is null
                 ORDER BY lower(a.name)
        """
        activities = self.fetchall(query)
        
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
        
        update = "update activities set category_id = -1 where category_id = ?"
        self.execute(update, (id, ))
        
        self.execute("delete from categories where id = ?", (id, ))
        
    
    def __swap_activities(self, id1, id2):
        """ swaps nearby activities """
        # TODO - 2 selects and 2 updates is wrong we could live without selects
        priority1 = self.fetchone("select activity_order from activities where id = ?", (id1,))[0]
        priority2 = self.fetchone("select activity_order from activities where id = ?", (id2,))[0]
        self.execute("update activities set activity_order = ? where id = ?", (priority1, id2) )
        self.execute("update activities set activity_order = ? where id = ?", (priority2, id1) )

    def __add_activity(self, name, category_id = None):
        # first check that we don't have anything like that yet
        activity_id = self.__get_activity_by_name(name, category_id)
        if activity_id:
            return activity_id
        
        #now do the create bit
        category_id = category_id or -1
        new_rec = self.fetchone("select max(id) + 1 , max(activity_order) + 1  from activities")
        new_id, new_order = new_rec[0] or 1, new_rec[1] or 1

        query = """
                   INSERT INTO activities (id, name, category_id, activity_order)
                        VALUES (?, ?, ?, ?)
        """
        self.execute(query, (new_id, name, category_id, new_order))
        return new_id

    def __update_activity(self, id, name, category_id):
        query = """
                   UPDATE activities
                       SET name = ?,
                           category_id = ?
                     WHERE id = ?
        """
        self.execute(query, (name, category_id, id))

    """ Here be dragons (lame connection/cursor wrappers) """
    def get_connection(self):
        if self.con == None:
            self.con = sqlite.connect(hamster.HAMSTER_DB, detect_types=sqlite.PARSE_DECLTYPES|sqlite.PARSE_COLNAMES)
            self.con.row_factory = sqlite.Row

        return self.con

    connection = property(get_connection, None)

    def fetchall(self, query, params = None):
        con = self.connection
        cur = con.cursor()

        print query, params

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
        con = self.connection
        cur = con.cursor()

        print statement, params
        res = cur.execute(statement, params)

        con.commit()
        cur.close()

    def run_fixtures(self):
        # defaults
        work_category = {"name": _("Work"),
                         "entries": [_("Reading news"),
                                     _("Checking stocks"),
                                     _("Super secret project X"),
                                     _("World domination")]}
        
        nonwork_category = {"name": _("Day to day"),
                            "entries": [_("Lunch"),
                                        _("Watering flowers"),
                                        _("Doing handstands")]}
        
        """upgrade DB to hamster version"""
        version = self.fetchone("SELECT version FROM version")["version"]
        current_version = 5

        if version < 2:
            """moving from fact_date, fact_time to start_time, end_time"""
    
            self.execute("""
                               CREATE TABLE facts_new
                                            (id integer primary key,
                                             activity_id integer,
                                             start_time varchar2(12),
                                             end_time varchar2(12))
            """)
    
            self.execute("""
                               INSERT INTO facts_new
                                           (id, activity_id, start_time)
                                    SELECT id, activity_id, fact_date || fact_time
                                      FROM facts
            """)

            self.execute("DROP TABLE facts")
            self.execute("ALTER TABLE facts_new RENAME TO facts")

            # run through all facts and set the end time
            # if previous fact is not on the same date, then it means that it was the
            # last one in previous, so remove it
            # this logic saves our last entry from being deleted, which is good
            facts = self.fetchall("""
                                        SELECT id, activity_id, start_time,
                                               substr(start_time,1, 8) start_date
                                          FROM facts
                                      ORDER BY start_time
            """)
            prev_fact = None
    
            for fact in facts:
                if prev_fact:
                    if prev_fact['start_date'] == fact['start_date']:
                        self.execute("UPDATE facts SET end_time = ? where id = ?",
                                   (fact['start_time'], prev_fact['id']))
                    else:
                        #otherwise that's the last entry of the day - remove it
                        self.execute("DELETE FROM facts WHERE id = ?", (prev_fact["id"],))
                
                prev_fact = fact

        #it was kind of silly not to have datetimes in first place
        if version < 3:
            self.execute("""
                               CREATE TABLE facts_new
                                            (id integer primary key,
                                             activity_id integer,
                                             start_time timestamp,
                                             end_time timestamp)
            """)
    
            self.execute("""
                               INSERT INTO facts_new
                                           (id, activity_id, start_time, end_time)
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

            self.execute("DROP TABLE facts")
            self.execute("ALTER TABLE facts_new RENAME TO facts")


        #adding categories table to categorize activities
        if version < 4:
            #adding the categories table
            self.execute("""
                               CREATE TABLE categories
                                            (id integer primary key,
                                             name varchar2(500),
                                             color_code varchar2(50),
                                             category_order integer)
            """)

            # adding default categories, and make sure that uncategorized stays on bottom for starters
            # set order to 2 in case, if we get work in next lines
            self.execute("""
                               INSERT INTO categories
                                           (id, name, category_order)
                                    VALUES (1, ?, 2);
               """, (nonwork_category["name"],))

            #check if we have to create work category - consider work everything that has been determined so, and is not deleted
            work_activities = self.fetchone("""
                                    SELECT count(*) as work_activities
                                      FROM activities
                                     WHERE deleted is null and work=1;
               """)['work_activities']
            
            if work_activities > 0:
                self.execute("""
                               INSERT INTO categories
                                           (id, name, category_order)
                                    VALUES (2, ?, 1);
                  """, (work_category["name"],))
            
            # now add category field to activities, before starting the move
            self.execute("""   ALTER TABLE activities
                                ADD COLUMN category_id integer;
               """)
            
            
            # starting the move
            
            # first remove all deleted activities with no instances in facts
            self.execute("""
                               DELETE FROM activities
                                     WHERE deleted = 1
                                       AND id not in(select activity_id from facts);
             """)

            
            # moving work / non-work to appropriate categories
            # exploit false/true = 0/1 thing
            self.execute("""       UPDATE activities
                                      SET category_id = work + 1
                                    WHERE deleted is null
               """)
            
            #finally, set category to -1 where there is none            
            self.execute("""       UPDATE activities
                                      SET category_id = -1
                                    WHERE category_id is null
               """)
            
            # drop work column and forget value of deleted
            # previously deleted records are now unsorted ones
            # user will be able to mark them as deleted again, in which case
            # they won't appear in autocomplete, or in categories
            # ressurection happens, when user enters the exact same name            
            self.execute("""
                               CREATE TABLE activities_new (id integer primary key,
                                                            name varchar2(500),
                                                            activity_order integer,
                                                            deleted integer,
                                                            category_id integer);
            """)
    
            self.execute("""
                               INSERT INTO activities_new
                                           (id, name, activity_order, category_id)
                                    SELECT id, name, activity_order, category_id
                                      FROM activities;
               """)

            self.execute("DROP TABLE activities")
            self.execute("ALTER TABLE activities_new RENAME TO activities")
        
        if version < 5:
            self.execute("ALTER TABLE facts add column description varchar2")


        # at the happy end, update version number 
        if version < current_version:
            #lock down current version
            self.execute("UPDATE version SET version = %d" % current_version) 
        

        
        """we start with an empty database and then populate with default
           values. This way defaults can be localized!"""
        
        category_count = self.fetchone("select count(*) from categories")[0]
        
        if category_count == 0:
            work_cat_id = self.__add_category(_(work_category["name"]))
            for entry in work_category["entries"]:
                self.__add_activity(_(entry), work_cat_id)
        
            nonwork_cat_id = self.__add_category(_(nonwork_category["name"]))
            for entry in nonwork_category["entries"]:
                self.__add_activity(_(entry), nonwork_cat_id)
        
        
        

