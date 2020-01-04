# This file is part of Hamster
# Copyright (c) The Hamster time tracker developers
# SPDX-License-Identifier: GPL-3.0-or-later


"""Hamster datetime.

Python datetime replacement, tuned for hamster use.
"""


import logging
logger = logging.getLogger(__name__)   # noqa: E402

import datetime as pdt  # standard datetime
import re

from collections import namedtuple
from textwrap import dedent
from functools import lru_cache


DATE_FMT = "%Y-%m-%d"  # ISO format
TIME_FMT = "%H:%M"
DATETIME_FMT = "{} {}".format(DATE_FMT, TIME_FMT)


class datetime:  # predeclaration for return type annotations
    pass


class time:  # predeclaration for return type annotations
    pass


class date(pdt.date):
    """Hamster date.

    Should replace the python datetime.date in any customer code.

    Same as python date, with the addition of parse methods.
    """

    FMT = "%Y-%m-%d"  # ISO format

    def __new__(cls, year, month, day):
        return pdt.date.__new__(cls, year, month, day)

    @classmethod
    def parse(cls, s):
        """Return date from string."""
        m = cls.re.search(s)
        return cls(year=int(m.group('year')),
                   month=int(m.group('month')),
                   day=int(m.group('day'))
                   )

    @classmethod
    def pattern(cls, detailed=True):
        if detailed:
            return dedent(r"""
                (?P<year>\d{4})        # 4 digits
                -                      # dash
                (?P<month>\d{2})       # 2 digits
                -                      # dash
                (?P<day>\d{2})         # 2 digits
                """)
        else:
            return r"""\d{4}-\d{2}-\d{2}"""


# For datetime that will need to be outside the class.
# Same here for consistency
date.re = re.compile(date.pattern(), flags=re.VERBOSE)


class hday(date):
    """Hamster day.

    Same as date, but taking into account day-start.
    A day starts at conf.day_start and ends when the next day starts.
    """

    def __new__(cls, year, month, day):
        return date.__new__(cls, year, month, day)

    @property
    def end(self) -> datetime:
        """Day end."""
        return datetime.from_day_time(self + timedelta(days=1), self.start_time())

    @property
    def start(self) -> datetime:
        """Day start."""
        return datetime.from_day_time(self, self.start_time())

    @classmethod
    def start_time(cls) -> time:
        """Day start time."""
        # work around cyclic imports
        from hamster.lib.configuration import conf
        return conf.day_start

    @classmethod
    def today(cls):
        """Return the current hamster day."""
        return datetime.now().hday()


class time(pdt.time):
    """Hamster time.

    Should replace the python datetime.time in any customer code.
    Specificities:
    - rounded to minutes
    - conversion to and from string facilities
    """

    FMT = "%H:%M"  # e.g. 13:30
    # match time, such as "01:32", "13.56" or "0116"

    def __new__(cls,
                hour=0, minute=0,
                second=0, microsecond=0,
                tzinfo=None, fold=0):
            # round down to zero seconds and microseconds
            return pdt.time.__new__(cls,
                                    hour=hour, minute=minute,
                                    second=0, microsecond=0,
                                    tzinfo=None, fold=fold)

    @classmethod
    def _extract_time(cls, match, h="hour", m="minute"):
        """Extract time from a time.re match.

        Custom group names allow to use the same method
        for two times in the same regexp (e.g. for range parsing)

        h (str): name of the group containing the hour
        m (str): name of the group containing the minute

        seealso: time.parse
        """
        h_str = match.group(h)
        m_str = match.group(m)
        if h_str and m_str:
            hour = int(h_str)
            minute = int(m_str)
            return cls(hour, minute)
        else:
            return None

    @classmethod
    def parse(cls, s):
        """Parse time from string."""
        m = cls.re.search(s)
        return cls._extract_time(m) if m else None

    # For datetime that must be a method.
    # Same here for consistency.
    @classmethod
    def pattern(cls):
        """Return a time pattern with all group names."""

        # remove the indentation for easier debugging.
        return dedent(r"""
            (?P<hour>                         # hour
             [0-9](?=[,\.:])                  # positive lookahead:
                                              # allow a single digit only if
                                              # followed by a colon, dot or comma
             | [0-1][0-9]                     # 00 to 19
             | [2][0-3]                       # 20 to 23
            )
            [,\.:]?                           # Separator can be colon,
                                              # dot, comma, or nothing.
            (?P<minute>[0-5][0-9])            # minute (2 digits, between 00 and 59)
            (?!\d?-\d{2}-\d{2})               # Negative lookahead:
                                              # avoid matching date by inadvertance.
                                              # For instance 2019-12-05
                                              # might be caught as 2:01.
                                              # Requiring space or - would not work:
                                              # 2019-2025 is the 20:19-20:25 range.
            """)


# For datetime that will need to be outside the class.
# Same here for consistency
time.re = re.compile(time.pattern(), flags=re.VERBOSE)


class datetime(pdt.datetime):
    """Hamster datetime.

    Should replace the python datetime.datetime in any customer code.
    Specificities:
    - rounded to minutes
    - conversion to and from string facilities
    """

    def __new__(cls, year, month, day,
                hour=0, minute=0,
                second=0, microsecond=0,
                tzinfo=None, *, fold=0):
            # round down to zero seconds and microseconds
            return pdt.datetime.__new__(cls, year, month, day,
                                        hour=hour, minute=minute,
                                        second=0, microsecond=0,
                                        tzinfo=None, fold=fold)

    def __add__(self, other):
        # python datetime.__add__ was not type stable prior to 3.8
        return datetime.from_pdt(self.to_pdt() + other)

    # similar to https://stackoverflow.com/q/51966126/3565696
    # __getnewargs_ex__ did not work, brute force required
    def __deepcopy__(self, memo):
        return datetime(self.year, self.month, self.day,
                        self.hour, self.minute,
                        self.second, self.microsecond,
                        self.tzinfo, fold=self.fold)

    __radd__ = __add__

    def __sub__(self, other):
        # python datetime.__sub__ was not type stable prior to 3.8
        if isinstance(other, timedelta):
            return datetime.from_pdt(self.to_pdt() - other)
        elif isinstance(other, datetime):
            return timedelta.from_pdt(self.to_pdt() - other)
        else:
            raise NotImplementedError("subtract {}".format(type(other)))

    def __str__(self):
        if self.tzinfo:
            raise NotImplementedError("Stay tuned...")
        else:
            return self.strftime(DATETIME_FMT)

    @classmethod
    def _extract_datetime(cls, match, d="date", h="hour", m="minute", r="relative",
                          default_day=None):
        """extract datetime from a datetime.pattern match.

        Custom group names allow to use the same method
        for two datetimes in the same regexp (e.g. for range parsing)

        h (str): name of the group containing the hour
        m (str): name of the group containing the minute
        r (str): name of the group containing the relative time
        default_day (dt.date): the datetime will belong to this hamster day if
                               date is missing.
        """
        _time = time._extract_time(match, h, m)
        if _time:
            date_str = match.group(d)
            if date_str:
                _date = date.parse(date_str)
                return datetime.combine(_date, _time)
            else:
                return datetime.from_day_time(default_day, _time)
        else:
            relative_str = match.group(r)
            if relative_str:
                return timedelta(minutes=int(relative_str))
            else:
                return None

    # not a property, to match other extractions such as .date() or .time()
    def hday(self) -> hday:
        """Return the day belonged to.

        The hamster day start is taken into account.
        """

        # work around cyclic imports
        from hamster.lib.configuration import conf

        _day = hday(self.year, self.month, self.day)
        if self.time() < conf.day_start:
            # early morning, between midnight and day_start
            # => the hamster day is the previous civil day
            _day -= timedelta(days=1)

        # return only the date
        return _day

    @classmethod
    def from_day_time(cls, d: hday, t: time):
        """Return a datetime with time t belonging to day.

        The hamster day start is taken into account.
        """

        # work around cyclic imports
        from hamster.lib.configuration import conf

        if t < conf.day_start:
            # early morning, between midnight and day_start
            # => the hamster day is the previous civil day
            civil_date = d + timedelta(days=1)
        else:
            civil_date = d
        return cls.combine(civil_date, t)

    # Note: fromisoformat appears in python3.7

    @classmethod
    def from_pdt(cls, t):
        """Convert python datetime to hamster datetime."""
        return cls(t.year, t.month, t.day,
                   t.hour, t.minute,
                   t.second, t.microsecond,
                   t.tzinfo, fold=t.fold)

    @classmethod
    def now(cls):
        """Current datetime."""
        return cls.from_pdt(pdt.datetime.now())

    @classmethod
    def parse(cls, s, default_day=None):
        """Parse a datetime from text.

        default_day (dt.date):
            If start is given without any date (e.g. just hh:mm),
            put the corresponding datetime in default_day.
            Defaults to today.
        """

        # datetime.re is added below, after the class definition
        # it will be found at runtime
        m = datetime.re.search(s)
        return cls._extract_datetime(m, default_day=default_day) if m else None

    @classmethod
    @lru_cache()
    def pattern(cls, n=None):
        """Return a datetime pattern with all group names.

        If n is given, all groups are suffixed with str(n).
        """

        # remove the indentation => easier debugging.
        base_pattern = dedent(r"""
            (?P<whole>
                                              # note: need to double the brackets
                                              #       for .format
                (?<!\d{{2}})                  # negative lookbehind,
                                              # avoid matching 2019-12 or 2019-12-05
                (?P<relative>-\d{{1,3}})      # minus 1, 2 or 3 digits: relative time
            |                             # or
                (?P<date>{})?                 # maybe date
                \s?                           # maybe one space
                {}                            # time
            )
            """).format(date.pattern(), time.pattern())
        if n is None:
            return base_pattern
        else:
            to_replace = ("whole", "relative",
                          "year", "month", "day", "date", "tens", "hour", "minute")
            specifics = ["{}{}".format(s, n) for s in to_replace]
            res = base_pattern
            for src, dest in zip(to_replace, specifics):
                res = res.replace(src, dest)
            return res

    def to_pdt(self):
        """Convert to python datetime."""
        return pdt.datetime(self.year, self.month, self.day,
                            self.hour, self.minute,
                            self.second, self.microsecond,
                            self.tzinfo, fold=self.fold)


# outside class; need the class to be defined first
datetime.re = re.compile(datetime.pattern(), flags=re.VERBOSE)


class Range():
    """Time span between two datetimes."""

    # slight memory optimization; no further attributes besides start or end.
    __slots__ = ('start', 'end')

    def __init__(self, start=None, end=None):
        self.start = start
        self.end = end

    # allow start, end = range
    def __iter__(self):
        return (self.start, self.end).__iter__()

    def format(self, default_day=None):
        """Return a string representing the time range.

        Start date is shown only if start does not belong to default_day.
        End date is shown only if end does not belong to
        the same hamster day as start.
        """
        time_str = ""
        if self.start:
            if self.start.hday() != default_day:
                time_str += self.start.strftime(DATETIME_FMT)
            else:
                time_str += self.start.strftime(TIME_FMT)
        if self.end:
            if self.end.hday() != self.start.hday():
                end_time_str = self.end.strftime(DATETIME_FMT)
            else:
                end_time_str = self.end.strftime(TIME_FMT)
            time_str = "{} - {}".format(time_str, end_time_str)
        return time_str

    @classmethod
    def parse(cls, text,
              position="exact", separator="\s+", default_day=None, ref="now"):
        """Parse a start-end range from text.

        position (str): "exact" to match exactly the full text
                        "head" to search only at the beginning of text, and
                        "tail" to search only at the end.

        separator (str): regexp pattern (e.g. '\s+') meant to separate the datetime
                         from the rest. Discarded for "exact" position.

        default_day (date): If start is given without any date (e.g. just hh:mm),
                               put the corresponding datetime in default_day.
                               Defaults to today.
                               Note: the default end day is always the start day, so
                                     "2019-11-27 23:50 - 00:20" lasts 30 minutes.

        ref (datetime): reference for relative times
                           (e.g. -15: quarter hour before ref).
                           For testing purposes only
                           (note: this will be removed later on,
                            and replaced with datetime.now mocking in pytest).
                           For users, it should be "now".
        Return:
            (range, rest)
            range (Range): Range(None, None) if no match is found.
            rest (str): remainder of the text.
        """

        if ref == "now":
            ref = datetime.now()

        if default_day is None:
            default_day = hday.today()

        assert position in ("exact", "head", "tail"), "position unknown: '{}'".format(position)
        if position == "exact":
            p = "^{}$".format(cls.pattern())
        elif position == "head":
            # require at least a space after, to avoid matching 10.00@cat
            # .*? so rest is as little as possible
            p = "^{}{}(?P<rest>.*?)$".format(cls.pattern(), separator)
        elif position == "tail":
            # require at least a space after, to avoid matching #10.00
            # .*? so rest is as little as possible
            p = "^(?P<rest>.*?){}{}$".format(separator, cls.pattern())
        # no need to compile, recent patterns are cached by re
        m = re.search(p, text, flags=re.VERBOSE)

        if not m:
            return Range(None, None), text
        elif position == "exact":
            rest = ""
        else:
            rest = m.group("rest")

        if m.group('firstday'):
            # only day given for start
            firstday = hday.parse(m.group('firstday'))
            start = firstday.start
        else:
            firstday = None
            start = datetime._extract_datetime(m, d="date1", h="hour1",
                                               m="minute1", r="relative1",
                                               default_day=default_day)
            if isinstance(start, pdt.timedelta):
                # relative to ref, actually
                delta1 = start
                start = ref + delta1

        if m.group('lastday'):
            lastday = hday.parse(m.group('lastday'))
            end = lastday.end
        elif firstday:
            end = firstday.end
        else:
            end = datetime._extract_datetime(m, d="date2", h="hour2",
                                             m="minute2", r="relative2",
                                             default_day=start.hday())
            if isinstance(end, pdt.timedelta):
                # relative to start, actually
                delta2 = end
                if delta2 > pdt.timedelta(0):
                    # wip: currently not reachable
                    # (would need [-\+]\d{1,3} in the parser).
                    end = start + delta2
                elif ref and delta2 < pdt.timedelta(0):
                    end = ref + delta2
                else:
                    end = None

        return Range(start, end), rest

    @classmethod
    @lru_cache()
    def pattern(cls):
        return dedent(r"""
            (                    # start
              {}                 # datetime: relative1 or (date1, hour1, and minute1)
              |                  # or
              (?P<firstday>{})  # date without time
            )
            (

                (?P<separation>   # (only needed if end time is given)
                    \s?           # maybe one space
                    -             # dash
                    \s?           # maybe one space
                  |               # or
                    \s            # one space exactly
                )
            (                     # end
              {}                  # datetime: relative2 or (date2, hour2, and minute2)
              |                   # or
              (?P<lastday>{})     # date without time
            )
            )?                    # end time is facultative
            """.format(datetime.pattern(1), date.pattern(detailed=False),
                       datetime.pattern(2), date.pattern(detailed=False)))


class timedelta(pdt.timedelta):
    """Hamster timedelta.

    Should replace the python datetime.timedelta in any customer code.
    Specificities:
    - rounded to minutes
    - conversion to and from string facilities
    """

    def __new__(cls, days=0, seconds=0, microseconds=0,
                milliseconds=0, minutes=0, hours=0, weeks=0):
            # round down to zero seconds and microseconds
            return pdt.timedelta.__new__(cls,
                                         days=days,
                                         seconds=seconds,
                                         microseconds=microseconds,
                                         milliseconds=milliseconds,
                                         minutes=minutes,
                                         hours=hours,
                                         weeks=weeks)

    # timedelta subclassing is not type stable yet
    def __add__(self, other):
        return timedelta.from_pdt(self.to_pdt() + other)

    __radd__ = __add__

    def __sub__(self, other):
        return timedelta.from_pdt(self.to_pdt() - other)

    def __neg__(self):
        return timedelta.from_pdt(-self.to_pdt())

    @classmethod
    def from_pdt(cls, delta):
        """Convert python timedelta to hamster timedelta."""

        # Only days, seconds and microseconds are stored internally
        return cls(days=delta.days,
                   seconds=delta.seconds,
                   microseconds=delta.microseconds)

    def to_pdt(self):
        """Convert to python timedelta."""

        return pdt.timedelta(days=self.days,
                             seconds=self.seconds,
                             microseconds=self.microseconds)

    def format(self, fmt="human"):
        """Return a string representation, according to the format string fmt."""
        allowed = ("human", "HH:MM")

        total_s = self.total_seconds()
        if total_s < 0:
            # return a warning
            return "NEGATIVE"

        hours = int(total_s // 3600)
        minutes = int((total_s - 3600 * hours) // 60)

        if fmt == "human":
            if minutes % 60 == 0:
                # duration in round hours
                return "{}h".format(hours)
            elif hours == 0:
                # duration less than one hour
                return "{}min".format(minutes)
            else:
                # x hours, y minutes
                return "{}h {}min".format(hours, minutes)
        elif fmt == "HH:MM":
            return "{:02d}:{:02d}".format(hours, minutes)
        else:
            raise NotImplementedError(
                "'{}' not in allowed formats: {}".format(fmt, allowed))
