import logging
logger = logging.getLogger(__name__)   # noqa: E402

import datetime as dt
import re

from hamster.lib import datetime as hdt
from hamster.lib.stuff import (
    datetime_to_hamsterday,
    hamster_now,
    hamster_today,
    hamsterday_end,
    hamsterday_start,
    hamsterday_time_to_datetime,
)


DATE_FMT = "%Y-%m-%d"  # ISO format
TIME_FMT = "%H:%M"
DATETIME_FMT = "{} {}".format(DATE_FMT, TIME_FMT)
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


range_pattern = r"""
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
""".format(hdt.datetime.pattern(1), hdt.date.basic_pattern,
           hdt.datetime.pattern(2), hdt.date.basic_pattern)


def parse_datetime_range(text, position="exact", separator="\s+", default_day=None, ref="now"):
    """Parse a start-end range from text.

    position (str): "exact" to match exactly the full text
                    "head" to search only at the beginning of text, and
                    "tail" to search only at the end.

    separator (str): regexp pattern (e.g. '\s+') meant to separate the datetime
                     from the rest. Discarded for "exact" position.

    default_day (dt.date): If start is given without any date (e.g. just hh:mm),
                           put the corresponding datetime in default_day.
                           Defaults to hamster_today.
                           Note: the default end day is always the start day, so
                                 "2019-11-27 23:50 - 00:20" lasts 30 minutes.

    ref (dt.datetime): reference for relative times
                       (e.g. -15: quarter hour before ref).
                       For testing purposes only
                       (note: this will be removed later on,
                        and replaced with hamster_now mocking in pytest).
                       For users, it should be "now".
    Return:
        (start, end, rest)
    """

    if ref == "now":
        ref = hamster_now()

    if default_day is None:
        default_day = hamster_today()

    assert position in ("exact", "head", "tail"), "position unknown: '{}'".format(position)
    if position == "exact":
        p = "^{}$".format(range_pattern)
    elif position == "head":
        # require at least a space after, to avoid matching 10.00@cat
        # .*? so rest is as little as possible
        p = "^{}{}(?P<rest>.*?)$".format(range_pattern, separator)
    elif position == "tail":
        # require at least a space after, to avoid matching #10.00
        # .*? so rest is as little as possible
        p = "^(?P<rest>.*?){}{}$".format(separator, range_pattern)
    # no need to compile, recent patterns are cached by re
    m = re.search(p, text, flags=re.VERBOSE)

    if not m:
        return None, None, text
    elif position == "exact":
        rest = ""
    else:
        rest = m.group("rest")

    if m.group('firstday'):
        # only day given for start
        firstday = hdt.date.parse(m.group('firstday'))
        start = hamsterday_start(firstday)
    else:
        firstday = None
        start = hdt.datetime._extract_datetime(m, d="date1", h="hour1", m="minute1", r="relative1",
                                               default_day=default_day)
        if isinstance(start, dt.timedelta):
            # relative to ref, actually
            delta1 = start
            start = ref + delta1

    if m.group('lastday'):
        lastday = hdt.date.parse(m.group('lastday'))
        end = hamsterday_end(lastday)
    elif firstday:
        end = hamsterday_end(firstday)
    else:
        end =  hdt.datetime._extract_datetime(m, d="date2", h="hour2", m="minute2", r="relative2",
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

    return start, end, rest


def parse_fact(text, range_pos="head", default_day=None, ref="now"):
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
    start, end, remaining_text = parse_datetime_range(text, position=range_pos,
                                                      separator=ACTIVITY_SEPARATOR,
                                                      default_day=default_day)
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
