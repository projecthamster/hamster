# SPDX-License-Identifier: GPL-3.0-or-later


"""Hamster datetime.

Python datetime replacement, tuned for hamster use.
"""


import logging
logger = logging.getLogger(__name__)   # noqa: E402

import datetime as dt  # standard datetime
import re


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

    def __str__(self):
        if self.tzinfo:
            raise NotImplementedError("Stay tuned...")
        else:
            return self.strftime(DATETIME_FMT)
