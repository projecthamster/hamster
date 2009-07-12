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
import stuff
import os
import datetime as dt
from xml.dom.minidom import Document
import csv

def simple(facts, start_date, end_date, format, path):
    report_path = stuff.locale_from_utf8(path)
    
    if format == "tsv":
        writer = TSVWriter(report_path)
    elif format == "xml":
        writer = XMLWriter(report_path)
    elif format == "ical":
        writer = ICalWriter(report_path)
    else: #default to HTML
        writer = HTMLWriter(report_path, start_date, end_date)

    writer.write_report(facts)


class ReportWriter(object):
    #a tiny bit better than repeating the code all the time
    def __init__(self, path, datetime_format = "%Y-%m-%d %H:%M:%S"):
        self.file = open(path, "w")
        self.datetime_format = datetime_format
        
    def write_report(self, facts):
        try:
            for fact in facts:
                fact["name"]= fact["name"].encode('utf-8')
                fact["description"] = (fact["description"] or u"").encode('utf-8')
                fact["category"] = (fact["category"] or _("Unsorted")).encode('utf-8')
                
                if self.datetime_format:
                    fact["start_time"] = fact["start_time"].strftime(self.datetime_format)
                    
                    if fact["end_time"]:
                        fact["end_time"] = fact["end_time"].strftime(self.datetime_format)
                    else:
                        fact["end_time"] = ""                
                fact["delta"] = fact["delta"].seconds / 60 + fact["delta"].days * 24 * 60
    
                self._write_fact(self.file, fact)
    
            self._finish(self.file, facts)
        finally:
            self.file.close()
    
    def _start(self, file, facts):
        raise NotImplementedError
    
    def _write_fact(self, file, fact):
        raise NotImplementedError
        
    def _finish(self, file, facts):
        raise NotImplementedError
    
class ICalWriter(ReportWriter):
    """a lame ical writer, could not be bothered with finding a library"""
    def __init__(self, path):
        ReportWriter.__init__(self, path, datetime_format = "%Y%m%dT%H%M%S")
        self.file.write("BEGIN:VCALENDAR\nVERSION:1.0\n")

    
    def _write_fact(self, file, fact):
        #for now we will skip ongoing facts
        if not fact["end_time"]: return

        if fact["category"] == _("Unsorted"):
            fact["category"] = None
            
        self.file.write("""BEGIN:VEVENT
CATEGORIES:%(category)s
DTSTART:%(start_time)s
DTEND:%(end_time)s
SUMMARY:%(name)s
DESCRIPTION:%(description)s
END:VEVENT
""" % fact)
        
    def _finish(self, file, facts):
        self.file.write("END:VCALENDAR\n")

class TSVWriter(ReportWriter):
    def __init__(self, path):
        ReportWriter.__init__(self, path)
        self.csv_writer = csv.writer(self.file, dialect='excel-tab')

        headers = [_("activity"), _("start time"), _("end time"),
                   _("duration minutes"), _("category"), _("description")]
        self.csv_writer.writerow([h.encode('utf-8') for h in headers])

    def _write_fact(self, file, fact):
        self.csv_writer.writerow([fact[key] for key in ["name", "start_time",
                               "end_time", "delta", "category", "description"]])
    def _finish(self, file, facts):
        pass

class XMLWriter(ReportWriter):
    def __init__(self, path):
        ReportWriter.__init__(self, path)
        self.doc = Document()
        self.activity_list = self.doc.createElement("activities")
    
    def _write_fact(self, file, fact):
        activity = self.doc.createElement("activity")
        activity.setAttribute("name", fact["name"])
        activity.setAttribute("start_time", fact["start_time"])
        activity.setAttribute("end_time", fact["end_time"])
        activity.setAttribute("duration_minutes", str(fact["delta"]))
        activity.setAttribute("category", fact["category"])
        activity.setAttribute("description", fact["description"])
        self.activity_list.appendChild(activity)
        
    def _finish(self, file, facts):
        self.doc.appendChild(self.activity_list)        
        file.write(self.doc.toxml())



class HTMLWriter(ReportWriter):
    def __init__(self, path, start_date, end_date):
        ReportWriter.__init__(self, path, datetime_format = None)

        dates_dict = stuff.dateDict(start_date, "start_")
        dates_dict.update(stuff.dateDict(end_date, "end_"))
        if start_date.year != end_date.year:
            self.title = _(u"Overview for %(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif start_date.month != end_date.month:
            self.title = _(u"Overview for %(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        else:
            self.title = _(u"Overview for %(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict
    
        if start_date == end_date:
            self.title = _(u"Overview for %(start_B)s %(start_d)s, %(start_Y)s") % dates_dict

        self.sum_time = {}
        self.even_row = True

        """TODO bring template to external file or write to PDF"""
        
        self.file.write("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta name="author" content="hamster-applet" />
    <title>%(title)s</title>
    <style type="text/css">
        body {
            font-family: "Sans";
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
        .row0 {
                background-color: #EAE8E3;
        }

        .row1 {
                background-color: #ffffff;
        }   

    </style>
</head>
<body>
<h1>%(title)s</h1>""" % {"title": self.title} + """
<table>
    <tr>
        <th class="smallCell">""" + _("Date") + """</th>
        <th class="largeCell">""" + _("Activity") + """</th>
        <th class="smallCell">""" + _("Category") + """</th>
        <th class="smallCell">""" + _("Start") + """</th>
        <th class="smallCell">""" + _("End") + """</th>
        <th class="smallCell">""" + _("Duration") + """</th>
        <th class="largeCell">""" + _("Description") + """</th>
    </tr>""")
    
    def _write_fact(self, report, fact):
        end_time = fact["end_time"]
        
        # ongoing task in current day
        end_time_str = ""
        if end_time:
            end_time_str = end_time.strftime('%H:%M')

        category = ""
        if fact["category"] != _("Unsorted"): #do not print "unsorted" in list
            category = fact["category"]

        description = fact["description"] or ""            
            
        # fact date column in HTML report
        report.write("""<tr class="row%d">
                            <td class="smallCell">%s</td>
                            <td class="largeCell">%s</td>
                            <td class="smallCell">%s</td>
                            <td class="smallCell">%s</td>
                            <td class="smallCell">%s</td>
                            <td class="smallCell">%s</td>
                            <td class="largeCell">%s</td>
                        </tr>
                       """ % (int(self.even_row),
                              _("%(report_b)s %(report_d)s, %(report_Y)s") % stuff.dateDict(fact["start_time"], "report_"),
                              fact["name"],
                              category, 
                              fact["start_time"].strftime('%H:%M'),
                              end_time_str,
                              stuff.format_duration(fact["delta"]) or "",
                              description))

        self.even_row = not self.even_row            


        # save data for summary table
        if fact["delta"]:
            id_string = "<td class=\"smallCell\">%s</td><td class=\"largeCell\">%s</td>" % (fact["category"], fact["name"])
            self.sum_time[id_string] = self.sum_time.get(id_string, 0) + fact["delta"]
    
    def _finish(self, report, facts):
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
        even_row = False
        for key in sorted(self.sum_time.keys()):
            report.write("    <tr class=\"row%d\">%s<td class=\"smallCell\">%s</td></tr>\n" % (int(even_row), key, stuff.format_duration(self.sum_time[key])))
            tot_time += self.sum_time[key]
          
            even_row = not even_row

        report.write("    <tr><th colspan=\"2\" style=\"text-align:right;\">" + _("Total Time") + ":</th><th>%s</th></tr>\n" % (stuff.format_duration(tot_time)))
        report.write("</table>\n")
    
        report.write("</body>\n</html>")
    
