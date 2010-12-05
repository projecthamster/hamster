# - coding: utf-8 -

# Copyright (C) 2008-2010 Toms Bauģis <toms.baugis at gmail.com>

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
import calendar
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


def format_range(start_date, end_date):
    dates_dict = dateDict(start_date, "start_")
    dates_dict.update(dateDict(end_date, "end_"))

    if start_date == end_date:
        # label of date range if looking on single day
        # date format for overview label when only single day is visible
        # Using python datetime formatting syntax. See:
        # http://docs.python.org/library/time.html#time.strftime
        title = start_date.strftime(_("%B %d, %Y"))
    elif start_date.year != end_date.year:
        # label of date range if start and end years don't match
        # letter after prefixes (start_, end_) is the one of
        # standard python date formatting ones- you can use all of them
        # see http://docs.python.org/library/time.html#time.strftime
        title = _(u"%(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
    elif start_date.month != end_date.month:
        # label of date range if start and end month do not match
        # letter after prefixes (start_, end_) is the one of
        # standard python date formatting ones- you can use all of them
        # see http://docs.python.org/library/time.html#time.strftime
        title = _(u"%(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
    else:
        # label of date range for interval in same month
        # letter after prefixes (start_, end_) is the one of
        # standard python date formatting ones- you can use all of them
        # see http://docs.python.org/library/time.html#time.strftime
        title = _(u"%(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict

    return title



def week(view_date):
    # aligns start and end date to week
    start_date = view_date - dt.timedelta(view_date.weekday() + 1)
    start_date = start_date + dt.timedelta(locale_first_weekday())
    end_date = start_date + dt.timedelta(6)
    return start_date, end_date

def month(view_date):
    # aligns start and end date to month
    start_date = view_date - dt.timedelta(view_date.day - 1) #set to beginning of month
    first_weekday, days_in_month = calendar.monthrange(view_date.year, view_date.month)
    end_date = start_date + dt.timedelta(days_in_month - 1)
    return start_date, end_date


def duration_minutes(duration):
    """returns minutes from duration, otherwise we keep bashing in same math"""
    if isinstance(duration, list):
        res = dt.timedelta()
        for entry in duration:
            res += entry

        return duration_minutes(res)
    elif isinstance(duration, dt.timedelta):
        return duration.seconds / 60 + duration.days * 24 * 60
    else:
        return duration


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


class Fact(object):
    def __init__(self, activity, category = "", description = "", tags = "",
                 start_time = None, end_time = None, id = None, delta = None,
                 date = None, activity_id = None):
        """the category, description and tags can be either passed in explicitly
        or by using the "activity@category, description #tag #tag" syntax.
        explicitly stated values will take precedence over derived ones"""
        self.original_activity = activity # unparsed version, mainly for trophies right now
        self.activity = None
        self.category = None
        self.description = None
        self.tags = []
        self.start_time = None
        self.end_time = None
        self.id = id
        self.ponies = False
        self.delta = delta
        self.date = date
        self.activity_id = activity_id

        # parse activity
        input_parts = activity.strip().split(" ")
        if len(input_parts) > 1 and re.match('^-?\d', input_parts[0]): #look for time only if there is more
            potential_time = activity.split(" ")[0]
            potential_end_time = None
            if len(potential_time) > 1 and  potential_time.startswith("-"):
                #if starts with minus, treat as minus delta minutes
                self.start_time = dt.datetime.now() + dt.timedelta(minutes = int(potential_time))

            else:
                if potential_time.find("-") > 0:
                    potential_time, potential_end_time = potential_time.split("-", 2)
                    self.end_time = figure_time(potential_end_time)

                self.start_time = figure_time(potential_time)

            #remove parts that worked
            if self.start_time and potential_end_time and not self.end_time:
                self.start_time = None #scramble
            elif self.start_time:
                activity = activity[activity.find(" ")+1:]

        #see if we have description of activity somewhere here (delimited by comma)
        if activity.find(",") > 0:
            activity, self.description = activity.split(",", 1)
            self.description = self.description.strip()

            if "#" in self.description:
                self.description, self.tags = self.description.split("#", 1)
                self.tags = [tag.strip(", ") for tag in self.tags.split("#") if tag.strip(", ")]

        if activity.find("@") > 0:
            activity, self.category = activity.split("@", 1)
            self.category = self.category.strip()

        #this is most essential
        if any([b in activity for b in ("bbq", "barbeque", "barbecue")]) and "omg" in activity:
            self.ponies = True
            self.description = "[ponies = 1], [rainbows = 0]"

        #only thing left now is the activity name itself
        self.activity = activity.strip()

        tags = tags or ""
        if tags and isinstance(tags, basestring):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # override implicit with explicit
        self.category = category.replace("#", "").replace(",", "") or self.category or None
        self.description = (description or "").replace("#", "") or self.description or None
        self.tags =  tags or self.tags or []
        self.start_time = start_time or self.start_time or None
        self.end_time = end_time or self.end_time or None


    def __iter__(self):
        keys = {
            'id': int(self.id),
            'activity': self.activity,
            'category': self.category,
            'description': self.description,
            'tags': [tag.encode("utf-8").strip() for tag in self.tags.split(",")],
            'date': calendar.timegm(self.date.timetuple()),
            'start_time': calendar.timegm(self.start_time.timetuple()),
            'end_time': calendar.timegm(self.end_time.timetuple()) if self.end_time else "",
            'delta': self.delta.seconds + self.delta.days * 24 * 60 * 60 #duration in seconds
        }
        return iter(keys.items())


    def serialized_name(self):
        res = self.activity

        if self.category:
            res += "@%s" % self.category

        if self.description or self.tags:
            res += ",%s %s" % (self.description or "",
                               " ".join(["#%s" % tag for tag in self.tags]))
        return res

    def __str__(self):
        time = ""
        if self.start_time:
            self.start_time.strftime("%d-%m-%Y %H:%M")
        if self.end_time:
            time = "%s - %s" % (time, self.end_time.strftime("%H:%M"))
        return "%s %s" % (time, self.serialized_name())
