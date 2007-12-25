"""separate file for database operations"""

from pysqlite2 import dbapi2 as sqlite
import os, time
import datetime
import hamster

# we are saving data under $HOME/.gnome2/hamster-applet/hamster.db
con = None # Connection will be created on demand

def to_date(dateString):
    """converts ISO format (YYYYMMDDHHMI) date string to datetime"""
    year, month, day = int(dateString[:4]), int(dateString[4:6]), int(dateString[6:8])
    
    hour, min = None, None
    if len(dateString) > 8:
        hour, min = int(dateString[8:10]), int(dateString[10:12])    
    
    return datetime.datetime(year, month, day, hour, min)


def get_activity_by_name(name):
  """get most recent, preferably not deleted activity by it's name"""
  query = """SELECT * from activities 
              WHERE name = ? 
           ORDER BY deleted, id desc
              LIMIT 1
          """
  return fetchone(query, (name,))

def add_custom_fact(activity_name, activity_time):
  """adds custom fact to database. custom means either it is
     post-factum, or some one-time task"""
  
  pass # TODO - move everything to add_fact

def get_last_activity():
    query = """SELECT a.id AS id,
                      a.start_time AS start_time,
                      a.end_time AS end_time,
                      b.name AS name, b.id as activity_id
                 FROM facts a
            LEFT JOIN activities b ON a.activity_id = b.id
             ORDER BY a.start_time desc, a.id desc
                LIMIT 1
    """

    return fetchone(query)

def finish_activity(id, end_time = None):
    end_time = end_time or datetime.datetime.now()
    execute("UPDATE facts SET end_time = ? where id = ?", (end_time, id))

def get_facts(date):
    query = """SELECT a.id AS id,
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
    return fetchall(query, (date, date + datetime.timedelta(days = 1)))

def add_fact(activity_name, fact_time = None):
    start_time = fact_time or datetime.datetime.now()
    
    # try to lookup activity by it's name in db. active ones have priority
    activity = get_activity_by_name(activity_name)

    if not activity:
      # insert and mark as deleted at the same time
      # FIXME - we are adding the custom activity as work, user should be able
      #         to choose
      # TODO - this place needs to be refactored also
      activity = {'id': -1, 'order': -1, 'work': 1, 'name': activity_name}
      activity['id'] = update_activity(activity)
      remove_activity(activity['id']) # removing so custom stuff doesn't start to appear in menu


    # avoid dupes and facts shorter than minute
    prev_activity = get_last_activity()

    if prev_activity and prev_activity['start_time'].date() == start_time.date():
        if prev_activity['id'] == activity['id']:
            return
        
        # if the time  since previous task is about minute 
        # then we consider that user has apparently mistaken and delete
        # the previous task
        delta = (start_time - prev_activity['start_time'])
        
        if delta.days == 0 and 60 > delta.seconds > 0:
            hamster.db.remove_fact(prev_activity['id'])
            fact_time = prev_activity['start_time']
            prev_activity = None  # forget about previous as we just removed it
    
    # if we have previous activity - update end_time
    if prev_activity: #TODO - constraint the update within one day (say, 12 hours, not more)
        execute("UPDATE facts set end_time = ? where id = ?",
                (start_time, prev_activity["id"]))
    
    #add the new entry
    insert = """INSERT INTO facts(activity_id, start_time)
                     VALUES (?, ?)
             """
    execute(insert, (activity['id'], start_time))
    return get_last_activity()

def remove_fact(fact_id):
    execute("DELETE FROM facts where id = ?", (fact_id,))

def get_activity_list(pattern = "%"):
    """returns list of configured activities, in user specified order"""
    query = """SELECT *
                 FROM activities
                WHERE coalesce(deleted, 0) = 0
                  AND name like ?
             ORDER BY activity_order
    """
    activities = fetchall(query, (pattern, ))

    return activities

def remove_activity(id):
    """ sets activity to deleted = True """
    execute("update activities set deleted = 1 where id = ?", (id,))

def swap_activity(id1, id2):
    """ swaps nearby activities """
    # TODO - 2 selects and 2 updates is wrong we could live without selects
    priority1 = fetchone("select activity_order from activities where id = ?", (id1,))[0]
    priority2 = fetchone("select activity_order from activities where id = ?", (id2,))[0]


    execute("update activities set activity_order = ? where id = ?", (priority1, id2) )
    execute("update activities set activity_order = ? where id = ?", (priority2, id1) )

def update_activity(activity):
    if activity['work']:
        work = 1
    else:
        work = 0

    if activity['id'] == -1: # -1 means, we have a new entry!
        new_rec = fetchone("select max(id) +1 , max(activity_order) + 1  from activities")
        new_id, new_order = 0, 0
        if new_rec: # handle case when we have no activities at all
            new_id, new_order = new_rec[0], new_rec[1]

        insert = """insert into activities (id, name, work, activity_order)
                                    values (?, ?, ?, ?);"""
        execute(insert, (new_id, activity['name'], work, new_order))
        activity['id'] = new_id

    else: # Update
        update = "UPDATE activities SET name = ?, work = ? WHERE id = ?;"
        execute(update, (activity['name'], work, activity['id']))

    return activity['id']


""" Here be dragons (lame connection/cursor wrappers) """
def get_connection():
    global con
    if con == None:
        con = sqlite.connect(hamster.HAMSTER_DB, detect_types=sqlite.PARSE_DECLTYPES|sqlite.PARSE_COLNAMES)

    con.row_factory = sqlite.Row
    return con

def fetchall(query, params = None):
    con = get_connection()
    cur = con.cursor()

    print query, params

    if params:
        cur.execute(query, params)
    else:
        cur.execute(query)

    res = cur.fetchall()
    cur.close()

    return res

def fetchone(query, params = None):
    res = fetchall(query, params)
    if res:
        return res[0]
    else:
        return None

def execute(statement, params = ()):
    con = get_connection()
    cur = con.cursor()

    print statement, params
    res = cur.execute(statement, params)

    con.commit()
    cur.close()


