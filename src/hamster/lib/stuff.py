# - coding: utf-8 -

# Copyright (C) 2008-2010, 2014 Toms Bauģis <toms.baugis at gmail.com>

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
from gi.repository import Gtk as gtk
from gi.repository import Pango as pango

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
            formatted_duration += ("%dh") % (hours)
        elif hours == 0:
            # duration less than hour
            formatted_duration += ("%dmin") % (minutes % 60.0)
        else:
            # x hours, y minutes
            formatted_duration += ("%dh %dmin") % (hours, minutes % 60)
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
        title = start_date.strftime(("%B %d, %Y"))
    elif start_date.year != end_date.year:
        # label of date range if start and end years don't match
        # letter after prefixes (start_, end_) is the one of
        # standard python date formatting ones- you can use all of them
        # see http://docs.python.org/library/time.html#time.strftime
        title = (u"%(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s".encode('utf-8')) % dates_dict
    elif start_date.month != end_date.month:
        # label of date range if start and end month do not match
        # letter after prefixes (start_, end_) is the one of
        # standard python date formatting ones- you can use all of them
        # see http://docs.python.org/library/time.html#time.strftime
        title = (u"%(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s".encode('utf-8')) % dates_dict
    else:
        # label of date range for interval in same month
        # letter after prefixes (start_, end_) is the one of
        # standard python date formatting ones- you can use all of them
        # see http://docs.python.org/library/time.html#time.strftime
        title = (u"%(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s".encode('utf-8')) % dates_dict

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
