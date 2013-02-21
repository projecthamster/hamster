from lib import rt
import sys

rt_url = 'http://rt.easter-eggs.org/demos/stable/REST/1.0/'
tracker = rt.Rt(rt_url, 'john.foo', 'john.foo')
tracker.login()
query = "Subject like 'm' AND Status='open'"
tickets = tracker.search_raw(query)
#tickets = tracker.search_simple(query)
#tickets = tracker.search_simple(query)
sys.stdout.write(str(tickets))

#li = "poprawki".split(' ')
#query = " AND ".join(["Subject LIKE '%s'" % (q) for q in li])
#sys.stdout.write(query)


#name = "cobi poprawki rpi"
#q = "cobi rpi"
#q_li = q.split(' ')
#has = [s for s in q_li if s in name]
#sys.stdout.write(str(has))

#res = all(item in name for item in q.split(' '))
#sys.stdout.write(str(res))