# - coding: utf-8 -

# Copyright (C) 2008 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2008 Nathan Samson <nathansamson at gmail dot com>

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
from hamster import stuff, storage
import os
import datetime as dt
import webbrowser

def simple(facts, start_date, end_date):
    dates_dict = stuff.dateDict(start_date, "start_")
    dates_dict.update(stuff.dateDict(end_date, "end_"))
    
    
    if start_date.year != end_date.year:
        title = _(u"Overview for %(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
    elif start_date.month != end_date.month:
        title = _(u"Overview for %(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
    else:
        title = _(u"Overview for %(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict

    if start_date == end_date:
        title = _("Overview for %(start_B)s %(start_d)s, %(start_Y)s") % dates_dict
    

    report_path = os.path.join(os.path.expanduser("~"), "%s.html" % title)
    report = open(report_path, "w")    
    
    report.write("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta name="author" content="hamster-applet" />
    <title>%s</title>
    <style type="text/css">
        body {
            padding: 12px;
        }
        h1 {
            border-bottom: 1px solid gray;
            padding-bottom: 4px;
        }
        h2 {
            margin-top: 2em;
        }
        table {
            margin-left: 24px
        }
        th {
            text-align: left;
        }
        tr {
            padding: 6px;
        }
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
            <th>""" + _("Date") + """</th>
            <th>""" + _("Activity") + """</th>
            <th>""" + _("Category") + """</th>
            <th>""" + _("Start") + """</th>
            <th>""" + _("End") + """</th>
            <th>""" + _("Duration") + """</th>
        </tr>""")
    
    #get id of last activity so we know when to show current duration
    last_activity_id = storage.get_last_activity()["id"]
    sum_time = {}
    
    for fact in facts:
        duration = None
        end_time = fact["end_time"]
        
        # ongoing task in current day
        if not end_time and fact["id"] == last_activity_id:
            end_time = dt.datetime.now()

        end_time_str = ""
        if end_time:
            delta = end_time - fact["start_time"]
            duration = 24 * 60 * delta.days + delta.seconds / 60
            end_time_str = end_time.strftime('%H:%M')

        category = ""
        if fact["category"] != _("Unsorted"): #do not print "unsorted" in list
            category = fact["category"]
        # fact date column in HTML report
        report.write("""<tr>
                            <td>%s</td>
                            <td>%s</td>
                            <td>%s</td>
                            <td>%s</td>
                            <td>%s</td>
                            <td>%s</td>
</tr>""" % (_("%(report_b)s %(report_d)s, %(report_Y)s") % stuff.dateDict(fact["start_time"], "report_"),
            fact["name"],
            category, 
            fact["start_time"].strftime('%H:%M'),
            end_time_str,
            stuff.format_duration(duration) or ""))



        # save data for summary table
        if duration:
            id_string = "<td>%s</td><td>%s</td>" % (fact["category"], fact["name"])
            if id_string in sum_time:
                sum_time[id_string] += duration
            else:
                sum_time[id_string] = duration
     
    report.write("</table>")

    # summary table
    report.write("\n<h2>%s</h2>\n" % _("Summary of Activities"))
    report.write("""<table>
    <tr>
        <th>""" + _("Category") + """</th>
        <th>""" + _("Activity") + """</th>
        <th>""" + _("Duration") + """</th>
    </tr>\n""")
    tot_time = 0
    for key in sorted(sum_time.keys()):
        report.write("    <tr>%s<td>%s</td></tr>\n" % (key, stuff.format_duration(sum_time[key])))
        tot_time += sum_time[key]
    report.write("    <tr><th colspan=\"2\">Total Time:</th><th>%s</th></tr>\n" % (stuff.format_duration(tot_time)))
    report.write("</table>\n")

    report.write("</body>\n</html>")

    
    report.close()

    webbrowser.open_new("file://"+report_path)
    
