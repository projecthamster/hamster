# - coding: utf-8 -

# Copyright (C) 2008 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2008 Nathan Samson <nathansamson at gmail dot com>
# Copyright (C) 2008 Giorgos Logiotatidis  <seadog at sealabs dot net>

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
        title = _(u"Overview for %(start_B)s %(start_d)s, %(start_Y)s") % dates_dict
    

    report_path = os.path.join(os.path.expanduser("~"), "%s.html" % title)
    report_path = stuff.locale_from_utf8(report_path)
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
            font-family: "Sans" ;
            font-size: 12px;
            padding: 12px;
            color: #303030;
            
        }
        h1 {
            border-bottom: 2px solid #303030;
            padding-bottom: 4px;
        }
        h2 {
            margin-top: 2em;
            border-bottom: 2px solid #303030;
        }
        table {
            width:800px;
        }
        th {
            font-size: 14px;
            text-align: center;
            padding-bottom: 6px;
        }
  
        .smallCell {
            text-align: center;
            width: 100px;
            padding: 3px;
        }

        .largeCell {
            text-align: left;
            padding: 3px 3px 3px 5px;
        }     
        .row1 {
        	background-color: #EAE8E3;
        }

        .row2 {
        	background-color: #ffffff;
        }   

    </style>
</head>
<body>""" % title)    
  
    
    report.write("<h1>%s</h1>" % title)
    
    report.write("""<table>
        <tr>
            <th class="smallCell">""" + _("Date") + """</th>
            <th class="largeCell">""" + _("Activity") + """</th>
            <th class="smallCell">""" + _("Category") + """</th>
            <th class="smallCell">""" + _("Start") + """</th>
            <th class="smallCell">""" + _("End") + """</th>
            <th class="smallCell">""" + _("Duration") + """</th>
            <th class="largeCell">""" + _("Description") + """</th>
        </tr>""")
    
    sum_time = {}
    rowcount = 1
    
    for fact in facts:
        duration = None
        end_time = fact["end_time"]
        
        # ongoing task in current day
        end_time_str = ""
        if end_time:
            end_time_str = end_time.strftime('%H:%M')

        if fact["delta"]:
            duration = 24 * 60 * fact["delta"].days + fact["delta"].seconds / 60

        category = ""
        if fact["category"] != _("Unsorted"): #do not print "unsorted" in list
            category = fact["category"]

        description = fact["description"] or ""            
            
        # fact date column in HTML report
        report.write("""<tr class="row%s">
                            <td class="smallCell">%s</td>
                            <td class="largeCell">%s</td>
                            <td class="smallCell">%s</td>
                            <td class="smallCell">%s</td>
                            <td class="smallCell">%s</td>
                            <td class="smallCell">%s</td>
                            <td class="largeCell">%s</td>
                        </tr>
                       """ % (rowcount, _("%(report_b)s %(report_d)s, %(report_Y)s") % stuff.dateDict(fact["start_time"], "report_"),
            fact["name"],
            category, 
            fact["start_time"].strftime('%H:%M'),
            end_time_str,
            stuff.format_duration(duration) or "",
            description))
            
        if rowcount == 1:
            rowcount = 2
        else:
            rowcount = 1


        # save data for summary table
        if duration:
            id_string = "<td class=\"smallCell\">%s</td><td class=\"largeCell\">%s</td>" % (fact["category"], fact["name"])
            if id_string in sum_time:
                sum_time[id_string] += duration
            else:
                sum_time[id_string] = duration
     
    report.write("</table>")

    # summary table
    report.write("\n<h2>%s</h2>\n" % _("Totals"))
    report.write("""<table>
    <tr>
        <th class="smallCell">""" + _("Category") + """</th>
        <th class="largeCell">""" + _("Activity") + """</th>
        <th class="smallCell">""" + _("Duration") + """</th>
    </tr>\n""")
    tot_time = 0
    rowcount = 1
    for key in sorted(sum_time.keys()):
        report.write("    <tr class=\"row%s\">%s<td class=\"smallCell\">%s</td></tr>\n" % (rowcount, key, stuff.format_duration(sum_time[key])))
        tot_time += sum_time[key]
      
        if rowcount == 1:
            rowcount = 2
        else:
            rowcount = 1       
    report.write("    <tr><th colspan=\"2\" style=\"text-align:right;\">" + _("Total Time") + ":</th><th>%s</th></tr>\n" % (stuff.format_duration(tot_time)))
    report.write("</table>\n")

    report.write("</body>\n</html>")

    
    report.close()

    webbrowser.open_new("file://"+report_path)
    
