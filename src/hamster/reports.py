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
import os, sys
import datetime as dt
from xml.dom.minidom import Document
import csv
import copy
import itertools
import re
from string import Template

from configuration import runtime
from utils import stuff, trophies
from utils.i18n import C_

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

    # some assembly required - hidden - saved a report for single day
    if start_date == end_date:
        trophies.unlock("some_assembly_required")

    # I want this on my desk - generated over 10 different reports
    if trophies.check("on_my_desk") == False:
        current = trophies.increment("reports_generated")
        if current == 10:
            trophies.unlock("on_my_desk")


class ReportWriter(object):
    #a tiny bit better than repeating the code all the time
    def __init__(self, path, datetime_format = "%Y-%m-%d %H:%M:%S"):
        self.file = open(path, "w")
        self.datetime_format = datetime_format

    def write_report(self, facts):
        try:
            for fact in facts:
                fact.activity= fact.activity.encode('utf-8')
                fact.description = (fact.description or u"").encode('utf-8')
                fact.category = (fact.category or _("Unsorted")).encode('utf-8')

                if self.datetime_format:
                    fact.start_time = fact.start_time.strftime(self.datetime_format)

                    if fact.end_time:
                        fact.end_time = fact.end_time.strftime(self.datetime_format)
                    else:
                        fact.end_time = ""

                fact.tags = ", ".join(fact.tags)

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
        if not fact.end_time: return

        if fact.category == _("Unsorted"):
            fact.category = None

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
        self.csv_writer.writerow([fact.activity,
                                  fact.start_time,
                                  fact.end_time,
                                  fact.delta,
                                  fact.category,
                                  fact.description,
                                  fact.tags])
    def _finish(self, file, facts):
        pass

class XMLWriter(ReportWriter):
    def __init__(self, path):
        ReportWriter.__init__(self, path)
        self.doc = Document()
        self.activity_list = self.doc.createElement("activities")

    def _write_fact(self, file, fact):
        activity = self.doc.createElement("activity")
        activity.setAttribute("name", fact.activity)
        activity.setAttribute("start_time", fact.start_time)
        activity.setAttribute("end_time", fact.end_time)
        activity.setAttribute("duration_minutes", str(stuff.duration_minutes(fact.delta)))
        activity.setAttribute("category", fact.category)
        activity.setAttribute("description", fact.description)
        activity.setAttribute("tags", fact.tags)
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
            self.title = _(u"Activity log for %(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif start_date.month != end_date.month:
            self.title = _(u"Activity log for %(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif start_date == end_date:
            self.title = _(u"Activity log for %(start_B)s %(start_d)s, %(start_Y)s") % dates_dict
        else:
            self.title = _(u"Activity log for %(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict


        # read the template, allow override
        self.override = os.path.exists(os.path.join(runtime.home_data_dir, "report_template.html"))
        if self.override:
            template = os.path.join(runtime.home_data_dir, "report_template.html")
        else:
            template = os.path.join(runtime.data_dir, "report_template.html")

        self.main_template = ""
        with open(template, 'r') as f:
            self.main_template =f.read()


        self.fact_row_template = self._extract_template('all_activities')

        self.by_date_row_template = self._extract_template('by_date_activity')
        self.by_date_total_row_template = self._extract_template("by_date_category")
        self.by_activity_category_row_template = self._extract_template("by_activity_category")
        self.totals_row_template = self._extract_template("totals_activity")

        self.by_date_template = self._extract_template('by_date')

        self.fact_rows = []

    def _extract_template(self, name):
        pattern = re.compile('<%s>(.*)</%s>' % (name, name), re.DOTALL)

        match = pattern.search(self.main_template)

        if match:
            self.main_template = self.main_template.replace(match.group(), "$%s_rows" % name)
            return match.groups()[0]

        return ""


    def _write_fact(self, report, fact):
        # no having end time is fine
        end_time_str, end_time_iso_str = "", ""
        if fact.end_time:
            end_time_str = fact.end_time.strftime('%H:%M')
            end_time_iso_str = fact.end_time.isoformat()

        category = ""
        if fact.category != _("Unsorted"): #do not print "unsorted" in list
            category = fact.category


        data = dict(
            date = fact.date.strftime(
                   # date column format for each row in HTML report
                   # Using python datetime formatting syntax. See:
                   # http://docs.python.org/library/time.html#time.strftime
                   C_("html report","%b %d, %Y")),
            date_iso = fact.date.isoformat(),
            activity = fact.activity,
            category = category,
            tags = fact.tags,
            start = fact.start_time.strftime('%H:%M'),
            start_iso = fact.start_time.isoformat(),
            end = end_time_str,
            end_iso = end_time_iso_str,
            duration = stuff.format_duration(fact.delta) or "",
            duration_minutes = "%d" % (stuff.duration_minutes(fact.delta)),
            duration_decimal = "%.2f" % (stuff.duration_minutes(fact.delta) / 60.0),
            description = fact.description or ""
        )
        self.fact_rows.append(Template(self.fact_row_template).safe_substitute(data))


    def _finish(self, report, facts):
        # group by date
        name_category = lambda fact: (fact.category, fact.activity)

        by_date = []
        for date, date_facts in itertools.groupby(facts, lambda fact:fact.date):
            by_name = sorted(date_facts, key=name_category)

            by_date_rows = []
            for (category, activity), ac_facts in itertools.groupby(by_name, name_category):
                duration = dt.timedelta()
                for fact in ac_facts:
                    duration += fact.delta


                by_date_rows.append(Template(self.by_date_row_template).safe_substitute(
                                    dict(activity = activity,
                                         category = category,
                                         duration = stuff.format_duration(duration),
                                         duration_minutes = "%d" % (stuff.duration_minutes(fact.delta)),
                                         duration_decimal = "%.2f" % (stuff.duration_minutes(fact.delta) / 60.0),
                                        )
                                    ))

            by_date_total_rows = []
            for category, c_facts in itertools.groupby(by_name, lambda fact:fact.category):
                duration = dt.timedelta()
                for fact in c_facts:
                    duration += fact.delta


                by_date_total_rows.append(Template(self.by_date_total_row_template).safe_substitute(
                                          dict(category = category,
                                               duration = stuff.format_duration(duration),
                                               duration_minutes = "%d" % (stuff.duration_minutes(fact.delta)),
                                               duration_decimal = "%.2f" % (stuff.duration_minutes(fact.delta) / 60.0),
                                              )
                                          ))


            res = Template(self.by_date_template).safe_substitute(
                           dict(date = fact.date.strftime(
                                       # date column format for each row in HTML report
                                       # Using python datetime formatting syntax. See:
                                       # http://docs.python.org/library/time.html#time.strftime
                                       C_("html report","%b %d, %Y")),
                                by_date_activity_rows = "\n".join(by_date_rows),
                                by_date_category_rows = "\n".join(by_date_total_rows)
                           ))
            by_date.append(res)

        by_activity_category_rows = []
        # group by activity
        name_category = lambda fact: (fact.category)
        name_activity = lambda fact: (fact.activity)

        total_duration = None
        by_category = sorted(facts, key=name_category)
        for category, category_facts in itertools.groupby(by_category, lambda fact:fact.category):
            by_activity = sorted(category_facts, key=name_activity)

            for (activity), ac_facts in itertools.groupby(by_activity, name_activity):
                duration = dt.timedelta()
                for fact in ac_facts:
                    duration += fact.delta

                by_activity_category_rows.append(Template(self.by_activity_category_row_template).safe_substitute(
                                        dict(activity = activity,
                                             category = category,
                                             duration = stuff.format_duration(duration),
                                             duration_minutes = "%d" % (stuff.duration_minutes(fact.delta)),
                                             duration_decimal = "%.2f" % (stuff.duration_minutes(fact.delta) / 60.0),
                                        )
                                    ))
                if (total_duration):
                    total_duration += duration
                else:
                    total_duration = duration

        by_totals_rows = []
        if (len(by_activity_category_rows) > 0):
            by_totals_rows.append(Template(self.totals_row_template).safe_substitute(
                                  dict(total_duration = stuff.format_duration(total_duration),
                                         total_duration_minutes = "%d" % (stuff.duration_minutes(total_duration)),
                                         total_duration_decimal = "%.2f" % (stuff.duration_minutes(total_duration) / 60.0),
                                         total_row = _("Total")
                                    )
                                ))


        data = dict(
            title = self.title,
            totals_by_day_title = _("Totals by Day"),
            activity_log_title = _("Activity Log"),
            totals_title = _("Totals"),

            activity_totals_heading = _("totals by activity"),
            category_totals_heading = _("totals by category"),

            show_prompt = _("Show:"),

            header_date = _("Date"),
            header_activity = _("Activity"),
            header_category = _("Category"),
            header_tags = _("Tags"),
            header_start = _("Start"),
            header_end = _("End"),
            header_duration = _("Duration"),
            header_description = _("Description"),

            data_dir = runtime.data_dir,
            show_template = _("Show template"),
            template_instructions = _("You can override it by storing your version in %(home_folder)s") % {'home_folder': runtime.home_data_dir},

            all_activities_rows = "\n".join(self.fact_rows),
            by_date_rows = "\n".join(by_date),
            by_activity_category_rows = "\n".join(by_activity_category_rows),
            totals_activity_rows = "\n".join(by_totals_rows)
        )
        report.write(Template(self.main_template).safe_substitute(data))

        if self.override:
            # my report is better than your report - overrode and ran the default report
            trophies.unlock("my_report")

        return
