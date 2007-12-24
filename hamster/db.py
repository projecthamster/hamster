"""separate file for database operations"""

from pysqlite2 import dbapi2 as sqlite
import os, time
import hamster

# we are saving data under $HOME/.hamsterdb
con = None # Connection will be created on demand

def mins(normal_time):
    """ returns time in minutes since midnight"""
    return int(normal_time[:2]) * 60 + int(normal_time[2:4])


def get_activity_by_name(name):
  """get most recent, preferably not deleted activity 
     by it's name"""
  query = """SELECT * from activities 
              WHERE name = ? 
           ORDER BY deleted, id desc
              LIMIT 1
          """
  return fetchone(query, (name,))

def add_custom_fact(activity_name, activity_time):
  """adds custom fact to database. custom means either it is
     post-factum, or some one-time task"""
  
  # we keep year in db as int
  fact_date = int(time.strftime('%Y%m%d', activity_time))
  fact_time = time.strftime('%H%M', activity_time)
  
  activity = get_activity_by_name(activity_name)
  
  if not activity:
    # insert and mark as deleted at the same time
    # FIXME - we are adding the custom activity as work, user should be able
    #         to choose
    activity = {'id': -1, 'order': -1, 'work': 1, 'name': activity_name}
    activity['id'] = update_activity(activity)
    remove_activity(activity['id']) # removing so custom stuff doesn't start to appear in menu
  
  add_fact(activity['id'], fact_date, fact_time)

def get_last_activity():
    query = """SELECT a.id, a.fact_date, a.fact_time, b.name, b.id as activity_id
                 FROM facts a
            LEFT JOIN activities b ON a.activity_id = b.id
             ORDER BY a.fact_date desc, a.fact_time desc, a.id desc
                LIMIT 1
    """

    return fetchone(query)

def get_facts(date):
    query = """SELECT a.id, a.fact_date, a.fact_time, b.name, b.id as activity_id
                 FROM facts a
            LEFT JOIN activities b ON a.activity_id = b.id
                WHERE a.fact_date = ?
             ORDER BY a.fact_time
    """

    return fetchall(query, (date,))

def add_fact(activity_name, fact_date = None, fact_time = None):
    fact_date = fact_date or time.strftime('%Y%m%d')
    fact_time = fact_time or time.strftime('%H%M')
    
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

    if prev_activity and str(prev_activity['fact_date']) == fact_date:
        if prev_activity['id'] == activity['id']:
            return
        
        # if the time  since previous task is about minute 
        # then we consider that user has apparently mistaken and delete
        # the previous task
        current_mins = hamster.db.mins(fact_time)
        prev_mins = hamster.db.mins(prev_activity['fact_time'])
        
        if (1 >= current_mins - prev_mins >= 0): 
            hamster.db.remove_fact(prev_activity['id'])
            fact_time = prev_activity['fact_time']
        
    
    
    
    insert = """INSERT INTO facts(activity_id, fact_date, fact_time)
                     VALUES (?, ?, ?)
             """
    execute(insert, (activity['id'], fact_date, fact_time))
    return get_last_activity()

def remove_fact(fact_id):
    execute("DELETE FROM facts where id = ?", (fact_id,))

def get_activity_list():
    """returns list of configured activities, in user specified order"""
    query = """SELECT *
                 FROM activities
                WHERE coalesce(deleted, 0) = 0
             ORDER BY activity_order
    """
    activities = fetchall(query)

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
        con = sqlite.connect(hamster.HAMSTER_DB)

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

def execute(statement, params):
    con = get_connection()
    cur = con.cursor()

    print statement, params
    res = cur.execute(statement, params)

    con.commit()
    cur.close()


