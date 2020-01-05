# SPDX-License-Identifier: GPL-3.0-or-later


"""Python datetime.datetime replacement, tuned for hamster use."""


import logging
logger = logging.getLogger(__name__)   # noqa: E402

import datetime as dt


DATE_FMT = "%Y-%m-%d"  # ISO format
TIME_FMT = "%H:%M"
DATETIME_FMT = "{} {}".format(DATE_FMT, TIME_FMT)


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
