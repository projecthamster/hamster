import logging
logger = logging.getLogger(__name__)   # noqa: E402

import datetime as dt
import re

from hamster.lib.stuff import (
    datetime_to_hamsterday,
    hamsterday_time_to_datetime,
    hamster_now,
)


DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%H:%M"


# match #tag followed by any space or # that will be ignored
# tag must not contain '#' or ','
tag_re = re.compile(r"""
    \#          # hash character
    (?P<tag>
        [^#,]+  # (anything but hash or comma)
    )
    \s*         # maybe spaces
                # forbid double comma (tag can not be before the tags barrier)
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
time_re = re.compile(r"""
    ^                                 # start of string
    (?P<hour>[0-1]?[0-9] | [2][0-3])  # hour (2 digits, between 00 and 23)
    [:,\.]?                           # separator can be colon,
                                      #  dot, comma, or nothing
    (?P<minute>[0-5][0-9])            # minute (2 digits, between 00 and 59)
    $                                 # end of string
""", flags=re.VERBOSE)


def extract_time(match):
    """extract time from a time_re match."""
    hour = int(match.group('hour'))
    minute = int(match.group('minute'))
    return dt.time(hour, minute)


def figure_time(str_time):
    if not str_time or not str_time.strip():
        return None

    # strip everything non-numeric and consider hours to be first number
    # and minutes - second number
    numbers = re.split("\D", str_time)
    numbers = [x for x in numbers if x!=""]

    hours, minutes = None, None

    if len(numbers) == 1 and len(numbers[0]) == 4:
        hours, minutes = int(numbers[0][:2]), int(numbers[0][2:])
    else:
        if len(numbers) >= 1:
            hours = int(numbers[0])
        if len(numbers) >= 2:
            minutes = int(numbers[1])

    if (hours is None or minutes is None) or hours > 24 or minutes > 60:
        return None #no can do

    return hamster_now()


def parse_fact(text, phase=None, res=None, date=None):
    """tries to extract fact fields from the string
        the optional arguments in the syntax makes us actually try parsing
        values and fallback to next phase
        start -> [end] -> activity[@category] -> tags

        Returns dict for the fact and achieved phase

        TODO - While we are now bit cooler and going recursively, this code
        still looks rather awfully spaghetterian. What is the real solution?

        Tentative syntax:
        [date] start_time[-end_time] activity[@category][, description]{[,] { })#tag}
        According to the legacy tests, # were allowed in the description
    """
    now = hamster_now()

    # determine what we can look for
    phases = [
        "date",  # hamster day
        "start_time",
        "end_time",
        "tags",
        "description",
        "activity",
        "category",
    ]

    phase = phase or phases[0]
    phases = phases[phases.index(phase):]
    if res is None:
        res = {}

    text = text.strip()
    if not text:
        return res

    fragment = re.split("[\s|#]", text, 1)[0].strip()

    # remove a fragment assumed to be at the beginning of text
    remove_fragment = lambda text, fragment: text[len(fragment):]

    if "date" in phases:
        # if there is any date given, it must be at the front
        try:
            date = dt.datetime.strptime(fragment, DATE_FMT).date()
            remaining_text = remove_fragment(text, fragment)
        except ValueError:
            date = datetime_to_hamsterday(now)
            remaining_text = text
        return parse_fact(remaining_text, "start_time", res, date)

    if "start_time" in phases or "end_time" in phases:

        # -delta ?
        delta_re = re.compile("^-[0-9]{1,3}$")
        if delta_re.match(fragment):
            # TODO untested
            # delta_re was probably thought to be used
            # alone or together with a start_time
            # but using "now" prevents the latter
            res[phase] = now + dt.timedelta(minutes=int(fragment))
            remaining_text = remove_fragment(text, fragment)
            return parse_fact(remaining_text, phases[phases.index(phase)+1], res, date)

        # only starting time ?
        m = re.search(time_re, fragment)
        if m:
            time = extract_time(m)
            res[phase] = hamsterday_time_to_datetime(date, time)
            remaining_text = remove_fragment(text, fragment)
            return parse_fact(remaining_text, phases[phases.index(phase)+1], res, date)

        # start-end ?
        start, __, end = fragment.partition("-")
        m_start = re.search(time_re, start)
        m_end = re.search(time_re, end)
        if m_start and m_end:
            start_time = extract_time(m_start)
            end_time = extract_time(m_end)
            res["start_time"] = hamsterday_time_to_datetime(date, start_time)
            res["end_time"] = hamsterday_time_to_datetime(date, end_time)
            remaining_text = remove_fragment(text, fragment)
            return parse_fact(remaining_text, "tags", res, date)

    if "tags" in phases:
        # Need to start from the end, because
        # the description can hold some '#' characters
        tags = []
        remaining_text = text
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
        return parse_fact(remaining_text, "description", res, date)

    if "description" in phases:
        # first look for double comma (description hard left boundary)
        head, sep, description = text.partition(",,")
        res["description"] = description.strip()
        return parse_fact(head, "activity", res, date)

    if "activity" in phases:
        split = text.rsplit('@', maxsplit=1)
        activity = split[0]
        category = split[1] if len(split) > 1 else ""
        if looks_like_time(activity):
            # want meaningful activities
            return res
        res["activity"] = activity
        res["category"] = category
        return res

    return {}


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
