from hamster.lib import Fact
from datetime import datetime as dt, date, time as ti
import time
from itertools import groupby
import logging
import re

TICKET_NAME_REGEX = "^#(\d+): "

class ExportRow(object):
    def __init__(self, fact):
        self.fact = fact
        match = re.match(TICKET_NAME_REGEX, fact.activity)
        self.id = int(match.group(1))
        self.comment = self.get_text(fact)
        self.time_worked = 10

    def __eq__(self, other):
        return isinstance(other, ExportRow) and other.id == self.id \
           and other.comment == self.comment \
           and other.time_worked == self.time_worked \
           and other.fact.start_time == self.fact.start_time \
           and other.fact.end_time == self.fact.end_time \
           and other.fact.id == self.fact.id
           
#    def __cmp__(self, other):
#        return cmp(self.id, self.id)
    
    def __repr__(self):
        return self.fact.activity

    def get_text(self, fact):
        text = ""
        if fact.description:
            text += ": %s" % (fact.description)
        if fact.tags:
            text += " ("+", ".join(fact.tags)+")"
        return text

d = date(2005, 7, 14)
t = ti(12, 30)


facts = list([\
         Fact(activity = "#123: 1", category = "category", description = "description", id=1), \
         Fact(activity = "#123: 2", category = "category", description = "description", id=2), \
         Fact(activity = "#222: 3", category = "category", description = "description", id=6), \
         Fact(activity = "#123: 4", category = "category", description = "description", id=3), \
         Fact(activity = "#222: 5", category = "category", description = "description", id=7), \
         Fact(activity = "#123: 6", category = "category", description = "description", id=4), \
         Fact(activity = "#123: 7", category = "category", description = "description", id=5), \
        ])
rows = [ExportRow(fact) for fact in facts]

tickets = {}
for ticket, group in groupby(rows, lambda export_row: export_row.id):
    print ticket, list(group)
rows.sort(key = lambda row: row.id)
for ticket, group in groupby(rows, lambda export_row: export_row.id):
    print ticket, list(group)

logging.warn(tickets)