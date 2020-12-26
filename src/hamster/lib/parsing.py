import logging
logger = logging.getLogger(__name__)   # noqa: E402

import re

from hamster.lib import datetime as dt


# separator between times and activity
ACTIVITY_SEPARATOR = "\s+"


# match #tag followed by any space or # that will be ignored
# tag must not contain '#' or ','
tag_re = re.compile(r"""
    \#          # hash character
    (?P<tag>
        [^#,]+  # (anything but hash or comma)
    )
""", flags=re.VERBOSE)

tags_separator = re.compile(r"""
    ,{1,2}      # 1 or 2 commas
    \s*         # maybe spaces
    (?=\#)      # hash character (start of first tag, doesn't consume it)
""", flags=re.VERBOSE)


def parse_fact(text, range_pos="head", default_day=None, ref="now"):
    """Extract fact fields from the string.

    Returns found fields as a dict.

    Tentative syntax (not accurate):
    start [- end_time] activity[@category][, description][,]{ #tag}
    According to the legacy tests, # were allowed in the description
    """

    res = {}

    text = text.strip()
    if not text:
        return res

    # datetimes
    # force at least a space to avoid matching 10.00@cat
    (start, end), remaining_text = dt.Range.parse(text, position=range_pos,
                                                   separator=ACTIVITY_SEPARATOR,
                                                   default_day=default_day)
    res["start_time"] = start
    res["end_time"] = end

    # tags
    split = re.split(tags_separator, remaining_text, 1)
    remaining_text = split[0]
    tags_part = split[1] if len(split) > 1 else None
    if tags_part:
        tags = list(map(lambda x: x.strip(), re.findall(tag_re, tags_part)))
    else:
        tags = []
    res["tags"] = tags

    # description
    # first look for comma (description hard left boundary)
    head, sep, description = remaining_text.partition(",")
    res["description"] = description.strip()
    remaining_text = head.strip()

    # activity
    split = remaining_text.rsplit('@', maxsplit=1)
    activity = split[0]
    category = split[1] if len(split) > 1 else ""
    res["activity"] = activity
    res["category"] = category

    return res
