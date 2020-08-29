# - coding: utf-8 -

# Copyright (C) 2007-2009, 2012, 2014 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>

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

import logging
import time

from hamster.lib import Fact, stuff

logger = logging.getLogger(__name__)  # noqa: E402

from hamster.lib.cache import cache
from gi.repository import Gtk as gtk
from gi.repository import GLib as glib
import re
import urllib3

try:
    from jira.client import JIRA
except ImportError:
    JIRA = None

SOURCE_NONE = ""
SOURCE_JIRA = 'jira'
JIRA_ISSUE_NAME_REGEX = "^([a-zA-Z][a-zA-Z0-9]*-[0-9]+)"
ERROR_ADDITIONAL_MESSAGE = '\n\nCheck settings and reopen main window.'
MIN_QUERY_LENGTH = 3
CURRENT_USER_ACTIVITIES_LIMIT = 5


class ExternalSource(object):
    def __init__(self, conf):
        logger.debug('external init')
        #         gobject.GObject.__init__(self)
        self.source = conf.get("activities-source")
        # self.__gtg_connection = None
        self.jira = None
        self.jira_projects = None
        self.jira_issue_types = None
        self.jira_query = None
        self.__http = None

        try:
            self.__connect(conf)
        except Exception as e:
            error_msg = self.source + ' connection failed: ' + str(e)
            self.source = SOURCE_NONE
            self.__on_error(error_msg + ERROR_ADDITIONAL_MESSAGE)
            logger.warning(error_msg)

    def __connect(self, conf):
        if self.source == SOURCE_JIRA:
            if JIRA:
                self.__http = urllib3.PoolManager()
                self.__connect_to_jira(conf)
            else:
                self.source = SOURCE_NONE
                self.__on_error(_("Is Jira module installed (see README)? "
                                  "Didn't found it! "
                                  "External activities feature will be disabled."))

    def __connect_to_jira(self, conf):
        self.jira_url = conf.get("jira-url")
        self.jira_user = conf.get("jira-user")
        self.jira_pass = conf.get("jira-pass")
        self.jira_query = conf.get("jira-query")
        self.jira_category = conf.get("jira-category-field")
        self.jira_fields = ','.join(['summary', self.jira_category, 'issuetype', 'assignee', 'project', 'status'])
        logger.info("user: %s, pass: *****" % self.jira_user)
        if self.jira_url and self.jira_user and self.jira_pass and self.__is_connected(self.jira_url):
            options = {'server': self.jira_url}
            self.jira = JIRA(options, basic_auth=(self.jira_user, self.jira_pass), validate=True)
            self.jira_projects = self.__jira_get_projects()
            self.jira_issue_types = self.__jira_get_issue_types()
        else:
            self.source = SOURCE_NONE
            self.__on_error("Invalid Jira credentials")

    def get_activities(self, query=None):
        query = query.strip()
        if not self.source or not query:
            return []
        elif self.source == SOURCE_JIRA:
            activities = self.__jira_get_activities(query, self.jira_query)
            direct_issue = None
            if query and re.match(JIRA_ISSUE_NAME_REGEX, query):
                if self.__jira_is_issue_from_existing_project(query):
                    issue = self.jira.issue(query.upper(), fields=self.jira_fields)
                    if issue:
                        direct_issue = self.__jira_extract_activity_from_issue(issue)
                        if direct_issue not in activities:
                            activities.append(direct_issue)
            if len(activities) <= CURRENT_USER_ACTIVITIES_LIMIT and not direct_issue and len(query) >= MIN_QUERY_LENGTH:
                words = query.split(' ')
                # filter empty elements
                fragments = filter(len, [self.__generate_fragment_jira_query(word) for word in words])
                jira_query = " AND ".join(
                    fragments) + " AND resolution = Unresolved order by priority desc, updated desc"
                logging.info(jira_query)
                third_activities = self.__jira_get_activities('', jira_query)
                if activities and third_activities:
                    activities.append({"name": "---------------------", "category": "other open"})
                activities.extend(third_activities)
            return activities

    def __generate_fragment_jira_query(self, word):
        if word.upper() in self.jira_projects:
            return "project = " + word.upper()
        elif word.lower() in self.jira_issue_types:
            return "issuetype = " + word.lower()
        elif word:
            return "(assignee = '%s' OR summary ~ '%s*')" % (word, word)
        else:
            return ""

    def __jira_get_activities(self, query='', jira_query=None):
        activities = []
        try:
            results = self.__jira_search_issues(jira_query)
            for issue in results:
                activity = self.__jira_extract_activity_from_issue(issue)
                if query is None or all(item in activity['name'].lower() for item in query.lower().split(' ')):
                    activities.append(activity)
        except Exception as e:
            logger.warning(e)
        return activities

    def __jira_extract_activity_from_issue(self, issue):
        activity = {}
        issue_id = issue.key
        fields = issue.fields
        activity['name'] = str(issue_id) \
                           + ': ' + fields.summary.replace(",", " ") \
                           + " (%s)" % fields.status.name \
                           + (" 👨‍💼" + fields.assignee.name if fields.assignee else "")
        if hasattr(fields, self.jira_category):
            activity['category'] = str(getattr(fields, self.jira_category))
        else:
            activity['category'] = ""
        if not activity['category'] or activity['category'] == "None":
            try:
                activity['category'] = "%s/%s (%s)" % (fields.project.key, fields.issuetype.name, fields.project.name)
            except Exception as e:
                logger.warning(e)
        return activity

    def __jira_get_projects(self):
        return [project.key for project in self.jira.projects()]

    def __jira_get_issue_types(self):
        return [issuetype.name.lower() for issuetype in self.jira.issue_types()]

    @cache(seconds=30)
    def __jira_search_issues(self, jira_query=None):
        return self.jira.search_issues(jira_query, fields=self.jira_fields, maxResults=100)

    def __on_error(self, msg):
        glib.idle_add(self.__on_error_dialog, msg)

    def __on_error_dialog(self, msg):
        md = gtk.MessageDialog(None,
                               0, gtk.MessageType.ERROR,
                               gtk.ButtonsType.CLOSE, msg)
        md.run()
        md.destroy()

    # https://stackoverflow.com/questions/3764291/checking-network-connection
    def __is_connected(self, url):
        try:
            self.__http.request('GET', url, timeout=1)
            return True
        except Exception as err:
            logger.info(err)
            return False

    def __jira_is_issue_from_existing_project(self, issue):
        return issue.split('-', 1)[0].upper() in self.jira_projects

    def export(self, fact: Fact) -> bool:
        """
        :return: bool fact was exported
        """
        logger.info("Exporting %s" % fact.activity)
        if not fact.range.end:
            logger.info("Skipping fact without end date")
            return False
        if fact.exported:
            logger.info("Skipping exported fact")
            return False
        if self.source == SOURCE_JIRA:
            jira_match = re.match(JIRA_ISSUE_NAME_REGEX, fact.activity)
            if jira_match:
                issue_id = jira_match.group(1)
                comment = self.__get_comment_to_export(fact)
                time_worked = stuff.duration_minutes(fact.delta)
                try:
                    self.__jira_add_worklog(issue_id, comment, fact.range.start, int(time_worked))
                    return True
                except Exception as e:
                    logger.error(e)
            else:
                logger.warning("skipping fact %s - unknown issue" % fact.activity)
        else:
            logger.warning("invalid source, don't know where export to")
        return False

    def __get_comment_to_export(self, fact: Fact):
        text = ""
        if fact.description:
            text += "%s\n" % (fact.description)
        text += "%s, %s-%s" % (fact.date, fact.range.start.strftime("%H:%M"), fact.range.end.strftime("%H:%M"))
        if fact.tags:
            text += " (" + ", ".join(fact.tags) + ")"
        return text

    def __jira_add_worklog(self, issue_id, text, start_time, time_worked):
        """
        :type start_time: date
        :param time_worked: int time spent in minutes
        """
        logger.info(_("updating issue #%s: %s min, comment: \n%s") % (issue_id, time_worked, text))
        self.jira.add_worklog(issue=issue_id, comment=text, started=start_time, timeSpent="%sm" % time_worked)
