# - coding: utf-8 -

# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>
# Copyright (C) 2007-2012 Toms Baugis <toms.baugis@gmail.com>

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
logger = logging.getLogger(__name__)   # noqa: E402

from hamster.lib import datetime as dt

from textwrap import dedent

from hamster.lib.fact import Fact, FactError


class Storage(object):
    """Abstract storage.

    Concrete instances should implement the required private methods,
    such as __get_facts.
    """

    def run_fixtures(self):
        pass

    # signals that are called upon changes
    def tags_changed(self): pass
    def facts_changed(self): pass
    def activities_changed(self): pass

    def dispatch_overwrite(self):
        self.tags_changed()
        self.facts_changed()
        self.activities_changed()

    # facts
    @classmethod
    def check_fact(cls, fact, default_day=None):
        """Check Fact validity for inclusion in the storage.

        Raise FactError(message) on failure.
        """
        if fact.start_time is None:
            raise FactError("Missing start time")

        if fact.end_time and (fact.delta < dt.timedelta(0)):
            fixed_fact = Fact(start_time=fact.start_time,
                              end_time=fact.end_time + dt.timedelta(days=1))
            suggested_range_str = fixed_fact.range.format(default_day=default_day)
            # work around cyclic imports
            from hamster.lib.configuration import conf
            raise FactError(dedent(
                """\
                Duration would be negative.
                Working late ?
                This happens when the activity crosses the
                hamster day start time ({:%H:%M} from tracking settings).

                Suggestion: move the end to the next day; the range would become:
                {}
                (in civil local time)
                """.format(conf.day_start, suggested_range_str)
                ))

        if not fact.activity:
            raise FactError("Missing activity")

        if ',' in fact.category:
            raise FactError(dedent(
                """\
                Forbidden comma in category: '{}'
                Note: The description separator changed
                      from single comma to double comma ',,' (cf. PR #482).
                """.format(fact.category)
                ))

    def add_fact(self, fact, start_time=None, end_time=None, temporary=False):
        """Add fact.

        fact: either a Fact instance or
              a string that can be parsed through Fact.parse.

        note: start_time and end_time are used only when fact is a string,
              for backward compatibility.
              Passing fact as a string is deprecated
              and will be removed in a future version.
              Parsing should be done in the caller.
        """
        if isinstance(fact, str):
            logger.info("Passing fact as a string is deprecated")
            fact = Fact.parse(fact)
            fact.start_time = start_time
            fact.end_time = end_time

        # better fail before opening the transaction
        self.check_fact(fact)
        self.start_transaction()
        result = self.__add_fact(fact, temporary)
        self.end_transaction()

        if result:
            self.facts_changed()
        return result

    def get_fact(self, fact_id):
        """Get fact by id. For output format see GetFacts"""
        return self.__get_fact(fact_id)

    def update_fact(self, fact_id, fact, start_time=None, end_time=None, temporary=False):
        # better fail before opening the transaction
        self.check_fact(fact)
        self.start_transaction()
        self.__remove_fact(fact_id)
        # to be removed once update facts use Fact directly.
        if isinstance(fact, str):
            fact = Fact.parse(fact)
            fact = fact.copy(start_time=start_time, end_time=end_time)
        result = self.__add_fact(fact, temporary)
        if not result:
            logger.warning("failed to update fact {} ({})".format(fact_id, fact))
        self.end_transaction()
        if result:
            self.facts_changed()
        return result

    def stop_tracking(self, end_time):
        """Stops tracking the current activity"""
        facts = self.__get_todays_facts()
        if facts and not facts[-1].end_time:
            self.__touch_fact(facts[-1], end_time)
            self.facts_changed()


    def remove_fact(self, fact_id):
        """Remove fact from storage by it's ID"""
        self.start_transaction()
        fact = self.__get_fact(fact_id)
        if fact:
            self.__remove_fact(fact_id)
            self.facts_changed()
        self.end_transaction()


    def get_facts(self, start, end=None, search_terms="", limit=0, asc_by_date=True):
        range = dt.Range.from_start_end(start, end)
        return self.__get_facts(range, search_terms, limit, asc_by_date)


    def get_todays_facts(self):
        """Gets facts of today, respecting hamster midnight. See GetFacts for
        return info"""
        return self.__get_todays_facts()


    # categories
    def add_category(self, name):
        res = self.__add_category(name)
        self.activities_changed()
        return res

    def get_category_id(self, category):
        return self.__get_category_id(category)

    def update_category(self, id, name):
        self.__update_category(id, name)
        self.activities_changed()

    def remove_category(self, id):
        self.__remove_category(id)
        self.activities_changed()


    def get_categories(self):
        return self.__get_categories()


    # activities
    def add_activity(self, name, category_id = -1):
        new_id = self.__add_activity(name, category_id)
        self.activities_changed()
        return new_id

    def update_activity(self, id, name, category_id):
        self.__update_activity(id, name, category_id)
        self.activities_changed()

    def remove_activity(self, id):
        result = self.__remove_activity(id)
        self.activities_changed()
        return result

    def get_category_activities(self, category_id = -1):
        return self.__get_category_activities(category_id = category_id)

    def get_activities(self, search = ""):
        return self.__get_activities(search)

    def get_ext_activities(self, search = ""):
        return self.__get_ext_activities(search)

    def export_fact(self, fact_id):
        return self.__export_fact(fact_id)

    def change_category(self, id, category_id):
        changed = self.__change_category(id, category_id)
        if changed:
            self.activities_changed()
        return changed

    def get_activity_by_name(self, activity, category_id, resurrect = True):
        category_id = category_id or None
        if activity:
            return dict(self.__get_activity_by_name(activity, category_id, resurrect) or {})
        else:
            return {}

    # tags
    def get_tags(self, only_autocomplete):
        return self.__get_tags(only_autocomplete)

    def get_tag_ids(self, tags):
        tags, new_added = self.__get_tag_ids(tags)
        if new_added:
            self.tags_changed()
        return tags

    def update_autocomplete_tags(self, tags):
        changes = self.__update_autocomplete_tags(tags)
        if changes:
            self.tags_changed()
