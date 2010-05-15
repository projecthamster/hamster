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
from hamster.i18n import C_
import copy
import StringIO
import itertools

def simple(facts, start_date, end_date, format, path):
    facts = copy.deepcopy(facts) # dont want to do anything bad to the input
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

                fact["tags"] = ", ".join(fact["tags"])

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

        headers = [# column title in the TSV export format
                   _("activity"),
                   # column title in the TSV export format
                   _("start time"),
                   # column title in the TSV export format
                   _("end time"),
                   # column title in the TSV export format
                   _("duration minutes"),
                   # column title in the TSV export format
                   _("category"),
                   # column title in the TSV export format
                   _("description"),
                   # column title in the TSV export format
                   _("tags")]
        self.csv_writer.writerow([h.encode('utf-8') for h in headers])

    def _write_fact(self, file, fact):
        self.csv_writer.writerow([fact[key] for key in ["name", "start_time",
                               "end_time", "delta", "category", "description",
                               "tags"]])
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
        delta = fact["delta"].seconds / 60 + fact["delta"].days * 24 * 60
        activity.setAttribute("duration_minutes", delta)
        activity.setAttribute("category", fact["category"])
        activity.setAttribute("description", fact["description"])
        activity.setAttribute("tags", fact["tags"])
        self.activity_list.appendChild(activity)

    def _finish(self, file, facts):
        self.doc.appendChild(self.activity_list)
        file.write(self.doc.toxml())



class HTMLWriter(ReportWriter):
    class HTMLTable(object):
        def __init__(self, id, headers):
            self.output = StringIO.StringIO()
            self.cols = len(headers)
            self.even = True

            self.output.write('<table id="%s" class="%s">')

            if any(headers):
                self.output.write('  <tr>')
                for col in headers:
                    self.output.write('    <th>%s</th>' % (col or ""))
                self.output.write('  </tr>')

        def add_row(self, *cols):
            self.output.write('  <tr>')
            for col in cols:
                self.output.write('    <td class="%s">%s</td>' % (["even", "odd"][int(self.even)], col))
            self.output.write('  </tr>')
            self.even = not self.even

        def add_heading(self, label):
            self.output.write('  <tr>')
            self.output.write('    <th colspan="%d">%s</td>' % (self.cols, label))
            self.output.write('  </tr>')

        def __str__(self):
            return "%s</table>" % self.output.getvalue()



    def __init__(self, path, start_date, end_date):
        ReportWriter.__init__(self, path, datetime_format = None)

        dates_dict = stuff.dateDict(start_date, "start_")
        dates_dict.update(stuff.dateDict(end_date, "end_"))

        if start_date.year != end_date.year:
            self.title = _(u"Activity log for %(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif start_date.month != end_date.month:
            self.title = _(u"Activity log for %(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif start_date == end_date:
            self.title = _(u"Activity log for %(start_B)s %(start_d)s, %(start_Y)s") % dates_dict
        else:
            self.title = _(u"Activity log for %(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict


        headers = (_("Date"), _("Activity"), _("Category"), _("Tags"),
                   _("Start"), _("End"), _("Duration"), _("Description"))
        self.fact_table = self.HTMLTable("facts", headers)


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
            font-family: "sans-serif";
            font-size: 12px;
            padding: 12px;
            color: #303030;
        }

        table {
            margin-left: 24px;
        }

        h1 {
            border-bottom: 2px solid #303030;
            padding-bottom: 4px;
        }
        h2 {
            margin-top: 2em;
            border-bottom: 2px solid #303030;
        }
        th, td {
            text-align: left;
            padding: 3px;
            padding-right: 24px;
        }

        th {
            padding-top: 12px;
        }

        ul {padding-bottom: 12px; margin-left: 12px; padding-left: 0px; list-style: none}
        li {padding: 2px 0px; margin: 0}

        .even {background-color: #eee;}
        .odd {background-color: #ffffff;}

    </style>
</head>
<body>
<h1>%(title)s</h1>""" % {"title": self.title})



    def _write_fact(self, report, fact):
        # no having end time is fine
        end_time_str = ""
        if fact["end_time"]:
            end_time_str = fact["end_time"].strftime('%H:%M')

        category = ""
        if fact["category"] != _("Unsorted"): #do not print "unsorted" in list
            category = fact["category"]

        self.fact_table.add_row(fact["start_time"].strftime(
                                # date column format for each row in HTML report
                                # Using python datetime formatting syntax. See:
                                # http://docs.python.org/library/time.html#time.strftime
                                C_("html report","%b %d, %Y")),
                                fact["name"],
                                category,
                                fact["tags"],
                                fact["start_time"].strftime('%H:%M'),
                                end_time_str,
                                stuff.format_duration(fact["delta"]) or "",
                                fact["description"] or "")

    def _finish(self, report, facts):
        report.write(str(self.fact_table))

        # summary table
        report.write("\n<h2>%s</h2>\n" % _("Totals by category, activity"))

        report.write("<ul>")

        summary_table = self.HTMLTable("summary", ("", ""))

        for category, cat_facts in itertools.groupby(sorted(facts, key=lambda fact: fact['category']), lambda fact: fact['category']):
            cat_facts = list(cat_facts)
            cat_total = dt.timedelta()
            for fact in cat_facts:
                cat_total += fact['delta']

            report.write("<li>")
            report.write("<b>%s: %s</b>" % (category, stuff.format_duration(cat_total)))

            report.write("<ul>")
            for activity, act_facts in itertools.groupby(sorted(cat_facts, key=lambda fact: fact['name']), lambda fact: fact['name']):
                act_total = dt.timedelta()
                for fact in act_facts:
                    act_total += fact['delta']
                report.write("<li>%s: %s</li>" % (activity, stuff.format_duration(act_total)))

            report.write("</ul>")
        report.write("</ul>")

        report.write("</body>\n</html>")
