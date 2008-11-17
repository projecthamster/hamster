# - coding: utf-8 -

# Copyright (C) 2008 Toms Bauģis <toms.baugis at gmail.com>

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


# some widgets that repeat all over the place
# cells, columns, trees and other

import gtk
from hamster import storage
import pango
from pango import ELLIPSIZE_END

import datetime as dt

class CategoryCell(gtk.CellRendererText):
    def __init__(self):
        gtk.CellRendererText.__init__(self)        
        self.set_property('alignment', pango.ALIGN_RIGHT)
        
        insensitive_color = gtk.Label().style.fg[gtk.STATE_INSENSITIVE]
        self.set_property('foreground-gdk', insensitive_color)
        self.set_property('scale', pango.SCALE_SMALL)
        self.set_property('yalign', 0.0)

class ExpanderColumn(gtk.TreeViewColumn):
    def __init__(self, label, text):
        gtk.TreeViewColumn.__init__(self, label)
        
        self.set_expand(True)
        cell = gtk.CellRendererText()
        cell.set_property('ellipsize', ELLIPSIZE_END)
        self.pack_start(cell, True)
        self.set_attributes(cell, text=text)


def format_duration(minutes):
    if minutes == None:
        return None
    
    hours = minutes / 60
    days = hours / 24
    hours %= 24
    minutes = minutes % 60
    formatted_duration = ""
    
    #TODO - convert to list comprehension or that other thing
    if days > 0:
        formatted_duration += "%d:" % days
    formatted_duration += "%02d:%02d" % (hours, minutes)
            
    return formatted_duration

def dateDict(date, prefix):
    """converts date into dictionary, having prefix for all the keys"""
    res = {}
    
    res[prefix+"a"] = date.strftime("%a")
    res[prefix+"A"] = date.strftime("%A")
    res[prefix+"b"] = date.strftime("%b")
    res[prefix+"B"] = date.strftime("%B")
    res[prefix+"c"] = date.strftime("%c")
    res[prefix+"d"] = date.strftime("%d")
    res[prefix+"H"] = date.strftime("%H")
    res[prefix+"I"] = date.strftime("%I")
    res[prefix+"j"] = date.strftime("%j")
    res[prefix+"m"] = date.strftime("%m")
    res[prefix+"M"] = date.strftime("%M")
    res[prefix+"p"] = date.strftime("%p")
    res[prefix+"S"] = date.strftime("%S")
    res[prefix+"U"] = date.strftime("%U")
    res[prefix+"w"] = date.strftime("%w")
    res[prefix+"W"] = date.strftime("%W")
    res[prefix+"x"] = date.strftime("%x")
    res[prefix+"X"] = date.strftime("%X")
    res[prefix+"y"] = date.strftime("%y")
    res[prefix+"Y"] = date.strftime("%Y")
    res[prefix+"Z"] = date.strftime("%Z")
    
    return res

class DayStore(object):
    """A day view contains a treeview for facts of the day and another
       one for totals. It creates those widgets on init, use
       fill_view(store) to fill the tree and calculate totals """

    def __init__(self, date = None):
        date = date or dt.date.today()
        
        # ID, Time, Name, Duration, Date
        self.fact_store = gtk.ListStore(int, str, str, str, str)
        
        self.facts = storage.get_facts(date)
        self.totals = {}
        
        for fact in self.facts:
            duration = None
            
            if fact["end_time"]: # not set if just started
                delta = fact["end_time"] - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60
            elif fact["start_time"].date() == dt.date.today():  # give duration to today's last activity
                delta = dt.datetime.now() - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60
            
            fact_category = fact['category']
            
            if fact_category not in self.totals:
                self.totals[fact_category] = 0

            if duration:
                self.totals[fact_category] += duration

            current_duration = format_duration(duration)

            self.fact_store.append([fact['id'], fact['name'], 
                                    fact["start_time"].strftime("%H:%M"), 
                                    current_duration,
                                    fact["start_time"].strftime("%Y%m%d")])

