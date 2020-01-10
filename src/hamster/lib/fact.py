# SPDX-License-Identifier: GPL-3.0-or-later


"""Fact definition."""


import logging
logger = logging.getLogger(__name__)   # noqa: E402

import calendar

from copy import deepcopy
from textwrap import dedent

from hamster.lib import datetime as dt
from hamster.lib.parsing import TIME_FMT, DATETIME_FMT, parse_fact
from hamster.lib.stuff import (
    hamsterday_time_to_datetime,
    hamster_now,
    hamster_today,
)

class FactError(Exception):
    """Generic Fact error."""


class Fact(object):
    def __init__(self, activity="", category=None, description=None, tags=None,
                 start_time=None, end_time=None, id=None, activity_id=None):
        """Homogeneous chunk of activity.

        The category, description and tags must be passed explicitly.

        To provide the whole fact information as a single string,
        please use Fact.parse(string).

        id (int): id in the database.
                  Should be used with extreme caution, knowing exactly why.
                  (only for very specific direct database read/write)
        """

        self.activity = activity
        self.category = category
        self.description = description
        self.tags = tags or []
        self.start_time = start_time
        self.end_time = end_time
        self.id = id
        self.activity_id = activity_id

    # TODO: might need some cleanup
    def as_dict(self):
        date = self.date
        return {
            'id': int(self.id) if self.id else "",
            'activity': self.activity,
            'category': self.category,
            'description': self.description,
            'tags': [tag.strip() for tag in self.tags],
            'date': calendar.timegm(date.timetuple()) if date else "",
            'start_time': self.start_time if isinstance(self.start_time, str) else calendar.timegm(self.start_time.timetuple()),
            'end_time': self.end_time if isinstance(self.end_time, str) else calendar.timegm(self.end_time.timetuple()) if self.end_time else "",
            'delta': self.delta.total_seconds()  # ugly, but needed for report.py
        }

    @property
    def activity(self):
        """Activity name."""
        return self._activity

    @activity.setter
    def activity(self, value):
        self._activity = value.strip() if value else ""

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, value):
        self._category = value.strip() if value else ""

    def copy(self, **kwds):
        """Return an independent copy, with overrides as keyword arguments.

        By default, only copy user-visible attributes.
        To also copy the id, use fact.copy(id=fact.id)
        """
        fact = deepcopy(self)
        fact._set(**kwds)
        return fact

    @property
    def date(self):
        """hamster day, determined from start_time.

        Note: Setting date is a one-shot modification of
              the start_time and end_time (if defined),
              to match the given value.
              Any subsequent modification of start_time
              can result in different self.date.
        """
        return dt.get_day(self.start_time)

    @date.setter
    def date(self, value):
        if self.start_time:
            previous_start_time = self.start_time
            self.start_time = hamsterday_time_to_datetime(value, self.start_time.time())
            if self.end_time:
                # start_time date prevails.
                # Shift end_time to preserve the fact duration.
                self.end_time += self.start_time - previous_start_time
        elif self.end_time:
            self.end_time = hamsterday_time_to_datetime(value, self.end_time.time())

    @property
    def delta(self):
        """Duration (datetime.timedelta)."""
        end_time = self.end_time if self.end_time else hamster_now()
        return end_time - self.start_time

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value.strip() if value else ""

    @classmethod
    def parse(cls, string, range_pos="head", default_day=None, ref="now"):
        fact = Fact()
        for key, val in parse_fact(string, range_pos=range_pos,
                                   default_day=default_day, ref=ref).items():
            setattr(fact, key, val)
        return fact

    def serialized_name(self):
        res = self.activity

        if self.category:
            res += "@%s" % self.category

        if self.description:
            res += ',, '
            res += self.description

        if ('#' in self.activity
            or '#' in self.category
            or '#' in self.description
           ):
            # need a tag barrier
            res += ",, "

        if self.tags:
            # double comma is a left barrier for tags,
            # which is useful only if previous fields contain a hash
            res += " %s" % " ".join("#%s" % tag for tag in self.tags)
        return res

    def serialized_range(self, default_day=None):
        """Return a string representing the time range.

        Start date is shown only if start does not belong to default_day.
        End date is shown only if end does not belong to
        the same hamster day as start.
        """
        time_str = ""
        if self.start_time:
            if dt.get_day(self.start_time) != default_day:
                time_str += self.start_time.strftime(DATETIME_FMT)
            else:
                time_str += self.start_time.strftime(TIME_FMT)
        if self.end_time:
            if dt.get_day(self.end_time) != dt.get_day(self.start_time):
                end_time_str = self.end_time.strftime(DATETIME_FMT)
            else:
                end_time_str = self.end_time.strftime(TIME_FMT)
            time_str = "{} - {}".format(time_str, end_time_str)
        return time_str

    def serialized(self, range_pos="head", default_day=None):
        """Return a string fully representing the fact."""
        name = self.serialized_name()
        datetime = self.serialized_range(default_day)
        # no need for space if name or datetime is missing
        space = " " if name and datetime else ""
        assert range_pos in ("head", "tail")
        if range_pos == "head":
            return "{}{}{}".format(datetime, space, name)
        else:
            return "{}{}{}".format(name, space, datetime)

    def _set(self, **kwds):
        """Modify attributes.

        Private, used only in copy. It is more readable to be explicit, e.g.:
        fact.start_time = ...
        fact.end_time = ...
        """
        for attr, value in kwds.items():
            if not hasattr(self, attr):
                raise AttributeError(f"'{attr}' not found")
            else:
                setattr(self, attr, value)

    def __eq__(self, other):
        return (isinstance(other, Fact)
                and self.activity == other.activity
                and self.category == other.category
                and self.description == other.description
                and self.end_time == other.end_time
                and self.start_time == other.start_time
                and self.tags == other.tags
                )

    def __repr__(self):
        return self.serialized(default_day=None)
