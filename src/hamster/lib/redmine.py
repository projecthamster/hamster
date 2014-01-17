# redmine.py -- a python library that allows working with
# redmine - a project management software
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Author: Alex Lourie <djay.il@gmail.com> @alourie
# Redmine: Copyright (C) 2006-2013  Jean-Philippe Lang

import os
import requests
import json


class Redmine:

    def __init__(self, url=None, auth=None, pass_file=None):
        self.url = url
        self.session = requests.Session()
        self.session.auth = auth or self.get_redmine_auth(pass_file=pass_file)
        if not self.session.auth:
            raise Exception(
                "Error! No auth nor password file for redmine were given!"
            )
        self.session.verify = False
        self.session.headers = {'content-type': 'application/json'}

    def getProject(self, project_id=None, name=None):
        if not project_id and not name:
            return None

        if project_id and name:
            raise TypeError("Please specify id or name, not both.")

        project_id = project_id or name
        r = self.session.get(self.get_project_url(project_id=project_id))
        if r.status_code != requests.codes.ok:
            return False
        return self.Project(r.json())

    def getProjects(self):
        r = self.session.get(self.get_project_url(), data=json.dumps({'limit': 999}))
        if r.status_code != requests.codes.ok:
            return False
        return [self.Project(data) for data in json.loads(r.content)['projects']]

    def getIssue(self, issue_id):
        r = self.session.get(self.get_issue_url(issue_id))
        if r.status_code != requests.codes.ok:
            return False
        return self.Issue(json.loads(r.content))

    def getIssues(self, criteria=None):
        if criteria and not 'limit' in criteria:
            criteria.update({'limit': 100})
        elif not criteria:
            criteria = ({'limit': 100})
        r = self.session.get(self.get_issue_url(),
                       data=json.dumps(criteria))
        if r.status_code != requests.codes.ok:
            return False
        return [self.Issue(data) for data in json.loads(r.content)['issues']]

    def updateIssue(self, issue_id, data):
        r = self.session.put(self.get_issue_url(issue_id), data=json.dumps(data))
        return r

    def createIssue(self, data):
        r = self.session.post(self.get_issue_url(), data=json.dumps(data))
        return r
        
    def createTimeEntry(self, data):
        r = self.session.post(self.get_time_entry_url(), data=json.dumps(data))
        return r

    def get_project_url(self, project_id=None):
        if project_id:
            url = self.url + "/projects/%s.json" % project_id
        else:
            url = self.url + "/projects.json"
        return url

    def get_issue_url(self, issue_id=None):
        if issue_id:
            url = self.url + "/issues/%s.json" % issue_id
        else:
            url = self.url + "/issues.json"
        return url

    def get_time_entry_url(self, entry_id=None):
        if entry_id:
            url = self.url + "/time_entries/%s.json" % entry_id
        else:
            url = self.url + "/time_entries.json"
        return url

    def get_redmine_auth(self, pass_file=None):
        """docstring for redmine_auth"""
        if not os.path.exists(pass_file):
            raise OSError("Auth file %s doesn't exist." % pass_file)

        username = ''

        with open(pass_file) as f:
            for line in f.readlines():
                if line.startswith("REDMINE_KEY"):
                    username = line.split("=")[1].strip()

        return (username, 'dummy')

    class RedmineObj(object):

        def __init__(self, data, objType):
            if not isinstance(data, dict):
                raise TypeError("Data must be dict!")
            self.raw_data = data
            self.objType = objType
            self.to_obj(data)

        def to_obj(self, data):
            if self.objType in data:
                self.__dict__.update(**data[self.objType])
            else:
                self.__dict__.update(**data)

        def __repr__(self):
            t = self.get_data()
            output = "Redmine %s object:\n" % self.objType
            output = output + "{\n"
            for k in t:
                v = t[k]
                output = output + "    '%s': '%s',\n" % (k, v)
            output = output + "}"
            return output

        def get_data(self):
            return {
                item : value for item, value in
                self.__dict__.iteritems() if
                not item == 'raw_data'
            }

    class Project(RedmineObj):
        def __init__(self, data):
            super(Redmine.Project, self).__init__(data, 'project')

    class Issue(RedmineObj):
        def __init__(self, data):
            super(Redmine.Issue, self).__init__(data, 'issue')

