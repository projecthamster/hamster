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

import logging
import gtk
import pango
from pango import ELLIPSIZE_END

from itertools import groupby
import datetime as dt
import time
import re
import locale
import os

def format_duration(minutes, human = True):
    """formats duration in a human readable format.
    accepts either minutes or timedelta"""

    if isinstance(minutes, dt.timedelta):
        minutes = duration_minutes(minutes)

    if not minutes:
        if human:
            return ""
        else:
            return "00:00"

    hours = minutes / 60
    minutes = minutes % 60
    formatted_duration = ""

    if human:
        if minutes % 60 == 0:
            # duration in round hours
            formatted_duration += _("%dh") % (hours)
        elif hours == 0:
            # duration less than hour
            formatted_duration += _("%dmin") % (minutes % 60.0)
        else:
            # x hours, y minutes
            formatted_duration += _("%dh %dmin") % (hours, minutes % 60)
    else:
        formatted_duration += "%02d:%02d" % (hours, minutes)


    return formatted_duration

def duration_minutes(duration):
    """returns minutes from duration, otherwise we keep bashing in same math"""
    return duration.seconds / 60 + duration.days * 24 * 60


def load_ui_file(name):
    from configuration import runtime
    ui = gtk.Builder()
    ui.add_from_file(os.path.join(runtime.data_dir, name))
    return ui

def zero_hour(date):
    return dt.datetime.combine(date.date(), dt.time(0,0))

# it seems that python or something has bug of sorts, that breaks stuff for
# japanese locale, so we have this locale from and to ut8 magic in some places
# see bug 562298
def locale_from_utf8(utf8_str):
    try:
        retval = unicode (utf8_str, "utf-8").encode(locale.getpreferredencoding())
    except:
        retval = utf8_str
    return retval

def locale_to_utf8(locale_str):
    try:
        retval = unicode (locale_str, locale.getpreferredencoding()).encode("utf-8")
    except:
        retval = locale_str
    return retval

def locale_first_weekday():
    """figure if week starts on monday or sunday"""
    first_weekday = 6 #by default settle on monday

    try:
        process = os.popen("locale first_weekday week-1stday")
        week_offset, week_start = process.read().split('\n')[:2]
        process.close()
        week_start = dt.date(*time.strptime(week_start, "%Y%m%d")[:3])
        week_offset = dt.timedelta(int(week_offset) - 1)
        beginning = week_start + week_offset
        first_weekday = int(beginning.strftime("%w"))
    except:
        logging.warn("WARNING - Failed to get first weekday from locale")

    return first_weekday

class CategoryCell(gtk.CellRendererText):
    def __init__(self):
        gtk.CellRendererText.__init__(self)
        self.set_property('alignment', pango.ALIGN_RIGHT)

        insensitive_color = gtk.Label().style.fg[gtk.STATE_INSENSITIVE]
        self.set_property('foreground-gdk', insensitive_color)
        self.set_property('scale', pango.SCALE_SMALL)
        self.set_property('yalign', 0.0)


insensitive_color = gtk.Label().style.fg[gtk.STATE_INSENSITIVE].to_string()
def format_activity(name, category, description, pad_description = False):
    "returns pango markup for activity with category and description"
    text = name
    if category and category != _("Unsorted"):
        text += """ - <span color="%s" size="x-small">%s</span>""" % (insensitive_color, category)

    if description:
        text+= "\n"
        if pad_description:
            text += " " * 23

        text += """<span style="italic" size="small">%s</span>""" % description

    return text


def totals(iter, keyfunc, sumfunc):
    """groups items by field described in keyfunc and counts totals using value
       from sumfunc
    """
    data = sorted(iter, key=keyfunc)
    res = {}

    for k, group in groupby(data, keyfunc):
        res[k] = sum([sumfunc(entry) for entry in group])

    return res




def dateDict(date, prefix = ""):
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

    for i, value in res.items():
        res[i] = locale_to_utf8(value)

    return res

def escape_pango(text):
    if not text:
        return text

    text = text.replace ("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text

def figure_time(str_time):
    if not str_time or not str_time.strip():
        return None

    # strip everything non-numeric and consider hours to be first number
    # and minutes - second number
    numbers = re.split("\D", str_time)
    numbers = filter(lambda x: x!="", numbers)

    hours, minutes = None, None

    if len(numbers) == 1 and len(numbers[0]) == 4:
        hours, minutes = int(numbers[0][:2]), int(numbers[0][2:])
    else:
        if len(numbers) >= 1:
            hours = int(numbers[0])
        if len(numbers) >= 2:
            minutes = int(numbers[1])

    if (hours is None or minutes is None) or hours > 24 or minutes > 60:
        return None #no can do

    return dt.datetime.now().replace(hour = hours, minute = minutes,
                                     second = 0, microsecond = 0)

def parse_activity_input(text):
    """Currently pretty braindead function that tries to parse arbitrary input
    into a activity"""
    class InputParseResult(object):
        def __init__(self):
            self.activity_name = None
            self.category_name = None
            self.start_time = None
            self.end_time = None
            self.description = None
            self.tags = []


    res = InputParseResult()

    input_parts = text.split(" ")
    if len(input_parts) > 1 and re.match('^-?\d', input_parts[0]): #look for time only if there is more
        potential_time = text.split(" ")[0]
        potential_end_time = None
        if len(potential_time) > 1 and  potential_time.startswith("-"):
            #if starts with minus, treat as minus delta minutes
            res.start_time = dt.datetime.now() + dt.timedelta(minutes =
                                                                int(potential_time))

        else:
            if potential_time.find("-") > 0:
                potential_time, potential_end_time = potential_time.split("-", 2)
                res.end_time = figure_time(potential_end_time)

            res.start_time = figure_time(potential_time)

        #remove parts that worked
        if res.start_time and potential_end_time and not res.end_time:
            res.start_time = None #scramble
        elif res.start_time:
            text = text[text.find(" ")+1:]

    if text.find("@") > 0:
        text, res.category_name = text.split("@", 1)
        res.category_name = res.category_name.strip()

    #only thing left now is the activity name itself
    res.activity_name = text

    #this is most essential
    if (text.find("bbq") > -1 or text.find("barbeque") > -1
        or text.find("barbecue") > -1)  and text.find("omg") > -1:
        res.description = "[ponies = 1], [rainbows = 0]"

    return res
