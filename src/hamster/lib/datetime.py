# SPDX-License-Identifier: GPL-3.0-or-later


"""Hamster datetime.

Python datetime replacement, tuned for hamster use.
"""


import logging
logger = logging.getLogger(__name__)   # noqa: E402

import datetime as dt  # standard datetime
import re

from textwrap import dedent

# to be replaced soon
from hamster.lib.stuff import hamsterday_time_to_datetime

DATE_FMT = "%Y-%m-%d"  # ISO format
TIME_FMT = "%H:%M"
DATETIME_FMT = "{} {}".format(DATE_FMT, TIME_FMT)


class date(dt.date):
    """Hamster date.

    Should replace the python datetime.date in any customer code.

    Same a python date, with the addition of parse methods.
    """

    FMT = "%Y-%m-%d"  # ISO format
    basic_pattern = r"""\d{4}-\d{2}-\d{2}"""
    basic_re = re.compile(basic_pattern, flags=re.VERBOSE)
    detailed_pattern = r"""
        (?P<year>\d{4})        # 4 digits
        -                      # dash
        (?P<month>\d{2})       # 2 digits
        -                      # dash
        (?P<day>\d{2})         # 2 digits
    """
    detailed_re = re.compile(detailed_pattern, flags=re.VERBOSE)

    def __new__(cls, year, month, day):
        return dt.date.__new__(cls, year, month, day)

    @classmethod
    def parse(cls, s):
        """Return date from string."""
        m = cls.detailed_re.search(s)
        return cls(year=int(m.group('year')),
                   month=int(m.group('month')),
                   day=int(m.group('day'))
                   )


class time(dt.time):
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
            return dt.time.__new__(cls,
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

        # remove the indentation => easier debugging.
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


class datetime(dt.datetime):
    """Hamster datetime.

    Should replace the python datetime.datetime in any customer code.
    Specificities:
    - rounded to minutes
    - conversion to and from string facilities
    """

    def __new__(cls, year, month, day,
                hour=0, minute=0,
                second=0, microsecond=0,
                tzinfo=None, fold=0):
            # round down to zero seconds and microseconds
            return dt.datetime.__new__(cls, year, month, day,
                                       hour=hour, minute=minute,
                                       second=0, microsecond=0,
                                       tzinfo=None, fold=fold)

    @classmethod
    def _extract_datetime(cls, match, d="date", h="hour", m="minute", r="relative", default_day=None):
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
                return hamsterday_time_to_datetime(default_day, _time)
        else:
            relative_str = match.group(r)
            if relative_str:
                return timedelta(minutes=int(relative_str))
            else:
                return None

    @classmethod
    def parse(cls, s, default_day=None):
        """Parse a datetime from text.

        default_day (dt.date):
            If start is given without any date (e.g. just hh:mm),
            put the corresponding datetime in default_day.
            Defaults to hamster_today.
        """

        # datetime.re is added below, after the class definition
        # it will be found at runtime
        m = datetime.re.search(s)
        return cls._extract_datetime(m, default_day=default_day) if m else None

    @classmethod
    def pattern(cls, n=None):
        """Return a datetime pattern with all group names.

        If n is given, all groups are suffixed with n.
        """

        # remove the indentation => easier debugging.
        base_pattern = dedent(r"""
            (?P<whole>
                                              # (need to double the brackets for .format)
                (?<!\d{{2}})                  # negative lookbehind,
                                              # avoid matching 2019-12 or 2019-12-05
                (?P<relative>-\d{{1,3}})      # minus 1, 2 or 3 digits: relative time
            |                             # or
                (?P<date>{})?                 # maybe date
                \s?                           # maybe one space
                {}                            # time
            )
            """).format(date.detailed_pattern, time.pattern())
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

    def __str__(self):
        if self.tzinfo:
            raise NotImplementedError("Stay tuned...")
        else:
            return self.strftime(DATETIME_FMT)


# outside class; need the class to be defined first
datetime.re = re.compile(datetime.pattern(), flags=re.VERBOSE)


# no need to change this one for now
timedelta = dt.timedelta
