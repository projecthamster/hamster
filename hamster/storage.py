# - coding: utf-8 -

# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>
# Copyright (C) 2007-2009 Toms Baugis <toms.baugis@gmail.com>

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


import datetime

class Storage(object):
    def __init__(self, parent):
        self.parent = parent

    def run_fixtures(self):
        pass

    def dispatch(self, event, data):
        self.parent.dispatch(event, data)

    def dispatch_overwrite(self):
        self.dispatch('new_tags_added', ())
        self.dispatch('day_updated', ())
        self.dispatch('activity_updated', ())

    def get_tags(self, autocomplete = None):
        return self.__get_tags(autocomplete)

    def get_tag_ids(self, tags):
        tags, new_added = self.__get_tag_ids(tags)
        if new_added:
            self.dispatch('new_tags_added', ())
        return tags

    def update_autocomplete_tags(self, tags):
        changes = self.__update_autocomplete_tags(tags)
        if changes:
            self.dispatch('new_tags_added', ())

    def get_fact(self, id):
        return self.__get_fact(id)

    def add_fact(self, activity_name, tags, start_time = None, end_time = None,
                                      category_name = None, description = None):

        self.start_transaction()
        result = self.__add_fact(activity_name, tags, start_time, end_time, category_name, description)
        self.end_transaction()

        if result:
            self.dispatch('day_updated', result['start_time'])
        return result

    def touch_fact(self, fact, end_time = None):
        end_time = end_time or datetime.datetime.now()
        result = self.__touch_fact(fact, end_time)
        self.dispatch('day_updated', fact['start_time'])
        return result

    def get_facts(self, date, end_date = None, search_terms = ""):
        return self.__get_facts(date, end_date, search_terms)

    def get_popular_categories(self):
        return self.__get_popular_categories()

    def remove_fact(self, fact_id):
        fact = self.get_fact(fact_id)
        if fact:
            self.__remove_fact(fact_id)
            self.dispatch('day_updated', fact['start_time'])

    def update_fact(self, fact_id, activity_name, tags, start_time, end_time):
        now = datetime.datetime.now()
        self.start_transaction()

        fact = self.get_fact(fact_id)
        if fact:
            self.__remove_fact(fact_id)

        result = self.__add_fact(activity_name, tags, start_time, end_time)

        self.end_transaction()

        if result:
            self.dispatch('day_updated', result['start_time'])
        return result

    def get_activities(self, category_id = None):
        return self.__get_activities(category_id = category_id)

    def get_autocomplete_activities(self):
        return self.__get_autocomplete_activities()

    def get_last_activity(self):
        return self.__get_last_activity()

    def remove_activity(self, id):
        result = self.__remove_activity(id)
        self.dispatch('activity_updated', ())
        return result

    def remove_category(self, id):
        self.__remove_category(id)
        self.dispatch('activity_updated', ())

    def move_activity(self, source_id, target_order, insert_after = True):
        self.__move_activity(source_id, target_order, insert_after)
        self.dispatch('activity_updated', ())

    def change_category(self, id, category_id):
        changed = self.__change_category(id, category_id)
        if changed:
            self.dispatch('activity_updated', ())
        return changed

    def swap_activities(self, id1, priority1, id2, priority2):
        res = self.__swap_activities(id1, priority1, id2, priority2)
        self.dispatch('activity_updated', ())
        return res

    def update_activity(self, id, name, category_id):
        self.__update_activity(id, name, category_id)
        self.dispatch('activity_updated', ())

    def add_activity(self, name, category_id = -1):
        new_id = self.__add_activity(name, category_id)
        self.dispatch('activity_updated', ())
        return new_id

    def update_category(self, id, name):
        self.__update_category(id, name)
        self.dispatch('activity_updated', ())

    def add_category(self, name):
        res = self.__add_category(name)
        self.dispatch('activity_updated', ())
        return res


    def get_category_list(self):
        return self.__get_category_list()

    def get_category_by_name(self, category):
        return self.__get_category_by_name(category)

    def get_activity_by_name(self, activity, category_id):
        return self.__get_activity_by_name(activity, category_id)
