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
from hamster import stuff
import os
import datetime as dt

def simple(facts, start_date, end_date):
    if start_date.year != end_date.year:
        start_str = start_date.strftime('%B %d. %Y')
        end_str = end_date.strftime('%B %d. %Y')
    elif start_date.month != end_date.month:
        start_str = start_date.strftime('%B %d')
        end_str = end_date.strftime('%B %d')
    else:
        start_str = start_date.strftime('%B %d')
        end_str = end_date.strftime('%d, %Y')

    if start_date == end_date:
        title = _("Overview for %s") % (start_date.strftime('%B %d. %Y'))
    else:
        title = _("Overview for %s - %s") % (start_str, end_str)

    report_path = os.path.join(os.path.expanduser("~"), "%s.html" % title)
    report = open(report_path, "w")    
    
    report.write("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta name="author" content="hamster-applet" />
    <title>%s</title>
    <style>
        body {
            padding: 12px;
        }
        h1 {
            border-bottom: 1px solid gray;
            padding-bottom: 4px;
        }
        table {margin-left: 24px}
        th {
            text-align: left;
        }
        tr {padding: 6px;}
        td {
            padding: 2px;
            padding-right: 24px;
        }

    </style>
</head>
<body>""" % title)
    
    report.write("<h1>%s</h1>" % title)
    
    
    report.write("""<table>
        <tr>
            <th>Date</th>
            <th>Activity</th>
            <th>Category</th>
            <th>Start</th>
            <th>End</th>
            <th>Duration</th>
        </tr>""")
    
    
    for fact in facts:
        duration = None
        if fact["end_time"]: # not set if just started
            delta = fact["end_time"] - fact["start_time"]
            duration = 24 * delta.days + delta.seconds / 60
        elif fact["start_time"].date() == dt.date.today():
            delta = dt.datetime.now() - fact["start_time"]
            duration = 24 * delta.days + delta.seconds / 60                


        report.write("""<tr>
                            <td>%s</td>
                            <td>%s</td>
                            <td>%s</td>
                            <td>%s</td>
                            <td>%s</td>
                            <td>%s</td>
</tr>""" % (fact["start_time"].strftime("%d.%m.%y"),
            fact["name"],
            fact["category"] if fact["category"] != _("Unsorted") else "", #do not print unsorted
            fact["start_time"].strftime('%H:%M'),
            fact["end_time"].strftime('%H:%M'),
            stuff.format_duration(duration)))
    
    report.write("</table></body></html>")
    report.close()

    os.system("gnome-open %s" % report_path.replace(" ", "\ "))
    
