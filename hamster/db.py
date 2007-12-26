"""separate file for database operations"""

from pysqlite2 import dbapi2 as sqlite
import os, time
import datetime
import hamster
import hamster.storage

class Storage(hamster.storage.Storage):
    # we are saving data under $HOME/.gnome2/hamster-applet/hamster.db
    con = None # Connection will be created on demand

    def __get_activity_by_name(self, name):
        """get most recent, preferably not deleted activity by it's name"""
        query = """
                   SELECT * from activities 
                    WHERE name = ? 
                 ORDER BY deleted, id desc
                    LIMIT 1
        """
        return self.fetchone(query, (name,))

    def __get_fact(self, id):
        query = """
                   SELECT *
                     FROM facts
                    WHERE id = ? 
                    LIMIT 1
        """
        return self.fetchone(query, (id,))

    def __get_last_activity(self):
        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          b.name AS name, b.id as activity_id
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                 ORDER BY a.start_time desc, a.id desc
                    LIMIT 1
        """
        return self.fetchone(query)

    def __touch_fact(self, activity, end_time = None):
        id = activity['id']
        query = """
                   UPDATE facts
                      SET end_time = ?
                    WHERE id = ?
        """
        self.execute(query, (end_time, id))

    def __get_facts(self, date):
        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          b.name AS name, b.id as activity_id
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                    WHERE a.start_time >= ?
                      AND a.start_time < ?
                 GROUP BY a.id
                 ORDER BY a.start_time
        """
        date = datetime.datetime.combine(date, datetime.time())
        return self.fetchall(query, (date, date + datetime.timedelta(days = 1)))

    def __add_fact(self, activity_name, fact_time = None):
        start_time = fact_time or datetime.datetime.now()
        
        # try to lookup activity by it's name in db. active ones have priority
        activity = self.__get_activity_by_name(activity_name)

        if not activity:
            # insert and mark as deleted at the same time
            # FIXME - we are adding the custom activity as work, user should be able
            #         to choose
            # TODO - this place needs to be refactored also
            activity = {'id': -1, 'order': -1, 'work': 1, 'name': activity_name}
            activity['id'] = self.update_activity(activity)
            self.remove_activity(activity['id']) # removing so custom stuff doesn't start to appear in menu

        # avoid dupes and facts shorter than minute
        prev_activity = self.__get_last_activity()

        if prev_activity and prev_activity['start_time'].date() == start_time.date():
            if prev_activity['id'] == activity['id']:
                return
            
            # if the time  since previous task is about minute 
            # then we consider that user has apparently mistaken and delete
            # the previous task
            delta = (start_time - prev_activity['start_time'])
        
            if delta.days == 0 and 60 > delta.seconds > 0:
                self.remove_fact(prev_activity['id'])
                fact_time = prev_activity['start_time']
                prev_activity = None  # forget about previous as we just removed it
        
        # if we have previous activity - update end_time
        if prev_activity: #TODO - constraint the update within one day (say, 12 hours, not more)
            query = """
                       UPDATE facts
                          SET end_time = ?
                        WHERE id = ?
            """
            self.execute(query, (start_time, prev_activity["id"]))
    
        #add the new entry
        insert = """
                    INSERT INTO facts
                                (activity_id, start_time, end_time)
                         VALUES (?, ?, ?)
        """
        self.execute(insert, (activity['id'], start_time, start_time))
        return self.__get_last_activity()

    def __remove_fact(self, fact_id):
        query = """
                   DELETE FROM facts
                         WHERE id = ?
        """
        self.execute(query, (fact_id,))

    def __get_activity_list(self, pattern = "%"):
        """returns list of configured activities, in user specified order"""
        query = """
                   SELECT *
                     FROM activities
                    WHERE coalesce(deleted, 0) = 0
                      AND name like ?
                 ORDER BY activity_order
        """
        activities = self.fetchall(query, (pattern, ))

        return activities

    def __remove_activity(self, id):
        """ sets activity to deleted = True """
        query = """
                   UPDATE activities
                      SET deleted = 1
                    WHERE id = ?
        """
        self.execute(query, (id,))

    def __swap_activities(self, id1, id2):
        """ swaps nearby activities """
        # TODO - 2 selects and 2 updates is wrong we could live without selects
        priority1 = self.fetchone("select activity_order from activities where id = ?", (id1,))[0]
        priority2 = self.fetchone("select activity_order from activities where id = ?", (id2,))[0]
        self.execute("update activities set activity_order = ? where id = ?", (priority1, id2) )
        self.execute("update activities set activity_order = ? where id = ?", (priority2, id1) )

    def __update_activity(self, activity):
        if activity['work']:
            work = 1
        else:
            work = 0

        if activity['id'] == -1: # -1 means, we have a new entry!
            new_rec = self.fetchone("select max(id) +1 , max(activity_order) + 1  from activities")
            new_id, new_order = 0, 0
            if new_rec: # handle case when we have no activities at all
                new_id, new_order = new_rec[0], new_rec[1]

            query = """
                       INSERT INTO activities
                                   (id, name, work, activity_order)
                            VALUES (?, ?, ?, ?)
            """
            self.execute(query, (new_id, activity['name'], work, new_order))
            activity['id'] = new_id
        else: # Update
            query = """
                       UPDATE activities
                           SET name = ?,
                               work = ?
                         WHERE id = ?
            """
            self.execute(update, (activity['name'], work, activity['id']))

        return activity['id']

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
        """upgrade DB to hamster version"""
        version = self.fetchone("SELECT version FROM version")["version"]

        if version < 2:
            """moving from fact_date, fact_time to start_time, end_time"""
    
            #create new table and copy data
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
            #create new table and copy data
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

        #lock down current version
        self.execute("UPDATE version SET version = 3")

