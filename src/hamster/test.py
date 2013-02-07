from lib import rt
import sys

rt_url = 'http://rt.easter-eggs.org/demos/stable/REST/1.0/'
tracker = rt.Rt(rt_url, 'john.foo', 'john.foo')
tracker.login()
query = "Subject like 'ma' AND Status='open'"
tickets = tracker.search_simple(query)
tickets = tracker.search_simple(query)
tickets = tracker.search_simple(query)
sys.stdout.write(str(tickets))
