# This file is part of Hamster
# Copyright (c) The Hamster time tracker developers
# SPDX-License-Identifier: GPL-3.0-or-later


"""Fact definition."""


import logging
logger = logging.getLogger(__name__)   # noqa: E402

import calendar

from copy import deepcopy

from hamster.lib import datetime as dt
from hamster.lib.parsing import parse_fact


class FactError(Exception):
    """Generic Fact error."""


class Fact(object):
    def __init__(self, activity="", category=None, description=None, tags=None,
                 range=None, start=None, end=None, start_time=None, end_time=None,
                 id=None, activity_id=None):
        """Homogeneous chunk of activity.

        The category, description and tags must be passed explicitly.

        To provide the whole fact information as a single string,
        please use Fact.parse(string).

        range (dt.Range): time spanned by the fact. For convenience,
                          the `start` and `end` arguments can be given instead.
        start (dt.datetime); Start of the fact range.
                             Mutually exclusive with `range`.
        end (dt.datetime); End of the fact range.
                           Mutually exclusive with `range`.
        start_time (dt.datetime): Deprecated. Same as start.
        end_time (dt.datetime): Deprecated. Same as end.

        id (int): id in the database.
                  Should be used with extreme caution, knowing exactly why.
                  (only for very specific direct database read/write)
        """

        self.activity = activity
        self.category = category
        self.description = description
        self.tags = tags or []
        if range:
            assert not start, "range already given"
            assert not end, "range already given"
            assert not start_time, "range already given"
            assert not end_time, "range already given"
            self.range = range
        else:
            if start_time:
                assert not start, "use only start, not start_time"
                start = start_time
            if end_time:
                assert not end, "use only end, not end_time"
                end = end_time
            self.range = dt.Range(start, end)
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
            'start_time': self.range.start if isinstance(self.range.start, str) else calendar.timegm(self.range.start.timetuple()),
            'end_time': self.range.end if isinstance(self.range.end, str) else calendar.timegm(self.range.end.timetuple()) if self.range.end else "",
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
        return self.range.start.hday() if self.range.start else None

    @date.setter
    def date(self, value):
        if self.range.start:
            previous_start_time = self.range.start
            self.range.start = dt.datetime.from_day_time(value, self.range.start.time())
            if self.range.end:
                # start_time date prevails.
                # Shift end_time to preserve the fact duration.
                self.range.end += self.range.start - previous_start_time
        elif self.range.end:
            self.range.end = dt.datetime.from_day_time(value, self.range.end.time())

    @property
    def delta(self):
        """Duration (datetime.timedelta)."""
        end_time = self.range.end if self.range.end else dt.datetime.now()
        return end_time - self.range.start

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value.strip() if value else ""

    @property
    def end_time(self):
        """Fact range end.

        Deprecated, use self.range.end instead.
        """
        return self.range.end

    @end_time.setter
    def end_time(self, value):
        self.range.end = value

    @property
    def start_time(self):
        """Fact range start.

        Deprecated, use self.range.start instead.
        """
        return self.range.start

    @start_time.setter
    def start_time(self, value):
        self.range.start = value

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

    def serialized(self, range_pos="head", default_day=None):
        """Return a string fully representing the fact."""
        name = self.serialized_name()
        if range_pos == "head":
            # Is activity starting range-like ?
            subfact = Fact.parse(self.activity, range_pos=range_pos,
                                 default_day=default_day)
            need_explicit = bool(subfact.range)
        else:
            # TODO: should check last tag.
            need_explicit = False
        datetime = self.range.format(default_day=default_day,
                                     explicit_none=need_explicit)
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
        fact.range.start = ...
        fact.range.end = ...
        """
        for attr, value in kwds.items():
            if not hasattr(self, attr):
                raise AttributeError("'{attr}' not found".format(attr=attr))
            else:
                setattr(self, attr, value)

    def __eq__(self, other):
        return (isinstance(other, Fact)
                and self.activity == other.activity
                and self.category == other.category
                and self.description == other.description
                and self.range.end == other.range.end
                and self.range.start == other.range.start
                and self.tags == other.tags
                )

    def __repr__(self):
        return self.serialized(default_day=None)
