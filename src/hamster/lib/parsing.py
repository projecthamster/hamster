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
    (start, end), remaining_text = hdt.Range.parse(text, position=range_pos,
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
