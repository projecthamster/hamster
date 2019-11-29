import logging
logger = logging.getLogger(__name__)   # noqa: E402

import calendar
import datetime as dt
import re

from copy import deepcopy

from hamster.lib.stuff import (
    datetime_to_hamsterday,
    hamsterday_time_to_datetime,
    hamster_now,
)


DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%H:%M"


# match #tag followed by any space or # that will be ignored
# tag must not contain #, comma, or any space character
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


class Fact(object):
    def __init__(self, activity="", category=None, description=None, tags=None,
                 start_time=None, end_time=None, id=None, activity_id=None):
        """Homogeneous chunk of activity.

        The category, description and tags must be passed explicitly.

        To provide the whole fact information as a single string,
        please use Fact.parse(string).

        id (int): id in the database.
                  Should be used with extreme caution, knowing exactly why.
                  (only for very specific direct database read/write)
        """

        self.activity = activity
        self.category = category
        self.description = description
        self.tags = tags or []
        self.start_time = start_time
        self.end_time = end_time
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
            'start_time': self.start_time if isinstance(self.start_time, str) else calendar.timegm(self.start_time.timetuple()),
            'end_time': self.end_time if isinstance(self.end_time, str) else calendar.timegm(self.end_time.timetuple()) if self.end_time else "",
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
        return datetime_to_hamsterday(self.start_time)

    @date.setter
    def date(self, value):
        if self.start_time:
            previous_start_time = self.start_time
            self.start_time = hamsterday_time_to_datetime(value, self.start_time.time())
            if self.end_time:
                # start_time date prevails.
                # Shift end_time to preserve the fact duration.
                self.end_time += self.start_time - previous_start_time
        elif self.end_time:
            self.end_time = hamsterday_time_to_datetime(value, self.end_time.time())

    @property
    def delta(self):
        """Duration (datetime.timedelta)."""
        end_time = self.end_time if self.end_time else hamster_now()
        return end_time - self.start_time

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value.strip() if value else ""

    @classmethod
    def parse(cls, string, date=None):
        fact = Fact()
        fact.date = date
        phase = "start_time" if date else "date"
        for key, val in parse_fact(string, phase, {}, date).items():
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

    def serialized_time(self, prepend_date=True):
        time = ""
        if self.start_time:
            if prepend_date:
                time += self.date.strftime(DATE_FMT) + " "
            time += self.start_time.strftime(TIME_FMT)
        if self.end_time:
            time = "%s-%s" % (time, self.end_time.strftime(TIME_FMT))
        return time

    def serialized(self, prepend_date=True):
        """Return a string fully representing the fact."""
        name = self.serialized_name()
        datetime = self.serialized_time(prepend_date)
        # no need for space if name or datetime is missing
        space = " " if name and datetime else ""
        return "{}{}{}".format(datetime, space, name)

    def _set(self, **kwds):
        """Modify attributes.

        Private, used only in copy. It is more readable to be explicit, e.g.:
        fact.start_time = ...
        fact.end_time = ...
        """
        for attr, value in kwds.items():
            if not hasattr(self, attr):
                raise AttributeError(f"'{attr}' not found")
            else:
                setattr(self, attr, value)

    def __eq__(self, other):
        return (isinstance(other, Fact)
                and self.activity == other.activity
                and self.category == other.category
                and self.description == other.description
                and self.end_time == other.end_time
                and self.start_time == other.start_time
                and self.tags == other.tags
                )

    def __repr__(self):
        return self.serialized(prepend_date=True)


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


def default_logger(name):
    """Return a toplevel logger.

    This should be used only in the toplevel file.
    Files deeper in the hierarchy should use
    ``logger = logging.getLogger(__name__)``,
    in order to considered as children of the toplevel logger.

    Beware that without a setLevel() somewhere,
    the default value (warning) will be used, so no debug message will be shown.

    Args:
        name (str): usually `__name__` in the package toplevel __init__.py, or
                    `__file__` in a script file
                    (because __name__ would be "__main__" in this case).
    """

    # https://docs.python.org/3/howto/logging.html#logging-advanced-tutorial
    logger = logging.getLogger(name)

    # this is a basic handler, with output to stderr
    logger_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    logger_handler.setFormatter(formatter)
    logger.addHandler(logger_handler)

    return logger
