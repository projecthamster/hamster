import logging
logger = logging.getLogger(__name__)   # noqa: E402

import datetime as dt
import re

from datetime import date
from hamster.lib.stuff import (
    datetime_to_hamsterday,
    hamsterday_time_to_datetime,
    hamster_now,
)


DATE_FMT = "%Y-%m-%d"  # ISO format
TIME_FMT = "%H:%M"
# separator between times and activity
ACTIVITY_SEPARATOR = "\s+"


# match #tag followed by any space or # that will be ignored
# tag must not contain '#' or ','
tag_re = re.compile(r"""
    \#          # hash character
    (?P<tag>
        [^#,]+  # (anything but hash or comma)
    )
    \s*         # maybe spaces
                # forbid double comma (tag can not be before the tags barrier):
    ,?          # single comma (or none)
    \s*         # maybe space
    $           # end of text
""", flags=re.VERBOSE)

tags_separator = re.compile(r"""
    (,{0,2})    # 0, 1 or 2 commas
    \s*         # maybe spaces
    $           # end of text
""", flags=re.VERBOSE)

# match time, such as "01:32", "13.56" or "0116"
time_pattern = r"""
    (?P<hour>[0-1]?[0-9] | [2][0-3])  # hour (2 digits, between 00 and 23)
    [:,\.]?                           # separator can be colon,
                                      #  dot, comma, or nothing
    (?P<minute>[0-5][0-9])            # minute (2 digits, between 00 and 59)
"""
time_re = re.compile(time_pattern, flags=re.VERBOSE)


date_pattern = r"""        # ISO format
    (?P<year>\d{4})        # 4 digits
    -                      # dash
    (?P<month>\d{2})       # 2 digits
    -                      # dash
    (?P<day>\d{2})         # 2 digits
"""
date_re = re.compile(date_pattern, flags=re.VERBOSE)

dt_pattern = r"""
    (?P<whole>
        (?P<relative>-\d{{1,3}})      # minus 1, 2 or 3 digits: relative time
                                      # (need to double the brackets for .format)
    |                             # or
        (?P<date>{})?                 # maybe date
        \s?                           # maybe one space
        {}                            # time
    )
""".format(date_pattern, time_pattern)


# needed for range_pattern
def specific_dt_pattern(n):
    """Return a datetime pattern with all group names suffixed with n."""
    to_replace = ("whole", "relative", "year", "month", "day", "date", "hour", "minute")
    specifics = ["{}{}".format(s, n) for s in to_replace]
    res = dt_pattern
    for src, dest in zip(to_replace, specifics):
        res = res.replace(src, dest)
    return res


range_pattern = r"""
                  # start datetime,
                  # relative1 or (date1, hour1, and minute1):
    {}
    (

        (?P<separation>   # (only needed if end time is given)
            \s?           # maybe one space
            -             # dash
            \s?           # maybe one space
          |             # or
            \s            # one space exactly
        )
                  # end datetime,
                  # relative2 or (date2, hour2, and minute2):
    {}
    )?            # end time is facultative
""".format(specific_dt_pattern(1), specific_dt_pattern(2))


def extract_time(match, h="hour", m="minute"):
    """Extract time from a time_re match.

    h (str): name of the group containing the hour
    m (str): name of the group containing the minute
    """
    h_str = match.group(h)
    m_str = match.group(m)
    if h_str and m_str:
        hour = int(h_str)
        minute = int(m_str)
        return dt.time(hour, minute)
    else:
        return None


def parse_time(s):
    """Parse time from string."""
    m = time_re.search(s)
    return extract_time(m)


def parse_date(s):
    """Extract ISO date (YYYY-MM-DD) from string."""
    m = date_re.search(s)
    return dt.date(year=int(m.group('year')),
                   month=int(m.group('month')),
                   day=int(m.group('day'))
                   )


def extract_datetime(match, d="date", h="hour", m="minute", r="relative", default_day=None):
    """extract datetime from a dt_pattern match.

    h (str): name of the group containing the hour
    m (str): name of the group containing the minute
    r (str): name of the group containing the relative time
    default_day (dt.date): the datetime will belong to this hamster day if
                           date is missing.
    """
    time = extract_time(match, h, m)
    if time:
        date_str = match.group(d)
        if date_str:
            date = parse_date(date_str)
            return dt.datetime.combine(date, time)
        else:
            return hamsterday_time_to_datetime(default_day, time)
    else:
        relative_str = match.group(r)
        if relative_str:
            return dt.timedelta(minutes=int(relative_str))
        else:
            return None


def parse_datetime_range(text, position="head", separator="", ref="now"):
    """Parse a start-end range from text.

    position (str): "head" to search only at the beginning of text, and
                    "tail" to search only at the end.
    separator (str): regexp pattern (e.g. '\s+') meant to separate the datetime
                     from the rest.
    ref (dt.datetime): reference for relative times
                       (e.g. -15: quarter hour before ref).
                       If any date is missing, put the corresponding
                       datetime in the same hamster day as ref.
    Return:
        (start, end, rest)
    """

    if ref == "now":
        ref = hamster_now()

    assert position in ("head",), "position unknown: '{}'".format(position)
    if position == "head":
        # require at least a space after, to avoid matching 10.00@cat
        # .*? so rest is as little as possible
        p = "^{}{}(?P<rest>.*?)$".format(range_pattern, separator)
    # no need to compile, recent patterns are cached by re
    m = re.search(p, text, flags=re.VERBOSE)

    if not m:
        return None, None, text

    if isinstance(ref, dt.datetime):
        default_day = datetime_to_hamsterday(ref)
    else:
        # ref is already a hamster day
        default_day = ref

    start = extract_datetime(m, d="date1", h="hour1", m="minute1", r="relative1",
                             default_day=datetime_to_hamsterday(ref))
    if isinstance(start, dt.timedelta):
        # relative to ref, actually
        delta1 = start
        start = ref + delta1

    end = extract_datetime(m, d="date2", h="hour2", m="minute2", r="relative2",
                           default_day=datetime_to_hamsterday(start))
    if isinstance(end, dt.timedelta):
        # relative to start, actually
        delta2 = end
        if delta2 > dt.timedelta(0):
            # wip: currently not reachable (would need [-\+]\d{1,3} in the parser).
            end = start + delta2
        elif ref and delta2 < dt.timedelta(0):
            end = ref + delta2
        else:
            end = None

    rest = m.group("rest")

    return start, end, rest


def parse_fact(text, default_date=None, ref="now"):
    """Extract fact fields from the string.

    Returns found fields as a dict.

    Tentative syntax (not accurate):
    start [- end_time] activity[@category][,, description][,,]{ #tag}
    According to the legacy tests, # were allowed in the description
    """

    res = {}

    text = text.strip()
    if not text:
        return res

    # datetimes
    # force at least a space to avoid matching 10.00@cat
    start, end, remaining_text = parse_datetime_range(text, position="head",
                                                      separator=ACTIVITY_SEPARATOR)
    res["start_time"] = start
    res["end_time"] = end

    # tags
    # Need to start from the end, because
    # the description can hold some '#' characters
    tags = []
    while True:
        # look for tags separators
        # especially the tags barrier
        m = re.search(tags_separator, remaining_text)
        remaining_text = remaining_text[:m.start()]
        if m.group(1) == ",,":
            # tags  barrier found
            break

        # look for tag
        m = re.search(tag_re, remaining_text)
        if m:
            tag = m.group('tag').strip()
            # strip the matched string (including #)
            remaining_text = remaining_text[:m.start()]
            tags.append(tag)
        else:
            # no tag
            break

    # put tags back in input order
    res["tags"] = list(reversed(tags))

    # description
    # first look for double comma (description hard left boundary)
    head, sep, description = remaining_text.partition(",,")
    res["description"] = description.strip()
    remaining_text = head.strip()

    # activity
    split = remaining_text.rsplit('@', maxsplit=1)
    activity = split[0]
    category = split[1] if len(split) > 1 else ""
    if looks_like_time(activity):
        # want meaningful activities
        return res
    res["activity"] = activity
    res["category"] = category

    return res


_time_fragment_re = [
    re.compile("^-$"),
    re.compile("^([0-1]?[0-9]?|[2]?[0-3]?)$"),
    re.compile("^([0-1]?[0-9]|[2][0-3]):?([0-5]?[0-9]?)$"),
    re.compile("^([0-1]?[0-9]|[2][0-3]):([0-5][0-9])-?([0-1]?[0-9]?|[2]?[0-3]?)$"),
    re.compile("^([0-1]?[0-9]|[2][0-3]):([0-5][0-9])-([0-1]?[0-9]|[2][0-3]):?([0-5]?[0-9]?)$"),
]
def looks_like_time(fragment):
    if not fragment:
        return False
    return any((r.match(fragment) for r in _time_fragment_re))
