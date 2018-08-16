import calendar
import datetime as dt
import logging
import re

from hamster.lib.stuff import (
    datetime_to_hamsterday,
    hamsterday_time_to_datetime,
)


DATE_FMT = "%d-%m-%Y"
TIME_FMT = "%H:%M"


# match #tag followed by any space or # that will be ignored
# tag must not contain #, comma, or any space character
tag_re = re.compile(r"""
    [\s,]*     # any spaces or commas (or nothing)
    \#          # hash character
    ([^#\s]+)  # the tag (anything but # or spaces)
    [\s#,]*    # any spaces, #, or commas (or nothing)
    $           # end of text
""", flags=re.UNICODE | re.VERBOSE)


def figure_time(str_time):
    if not str_time or not str_time.strip():
        return None

    # strip everything non-numeric and consider hours to be first number
    # and minutes - second number
    numbers = re.split("\D", str_time)
    numbers = filter(lambda x: x!="", numbers)

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

    return dt.datetime.now().replace(hour = hours, minute = minutes,
                                     second = 0, microsecond = 0)


class Fact(object):
    def __init__(self, activity="", category = "", description = "", tags = "",
                 start_time = None, end_time = None, id = None, delta = None,
                 date = None, activity_id = None, initial_fact=None):
        """Homogeneous chunk of activity.
        The category, description and tags can be either passed in explicitly
        or by passing a string with the
        "activity@category, description #tag #tag"
        syntax as the first argument (activity), for historical reasons.
        Explicitly stated values will take precedence over derived ones.
        initial_fact (Fact or str): optional starting point.
                                    This is the same as calling
                                    Fact(str(initial_fact), ...)
        """

        # Previously the "activity" argument could only be a string,
        # actually containing all the "fact" information.
        # Now allow to pass an inital fact, that will be copied,
        # and overridden by any given keyword argument
        # Note: currently, the genuine activity (before the @)
        #       is the same as in the original fact
        if initial_fact:
            activity = initial_fact.serialized()

        self.original_activity = activity # unparsed version, mainly for trophies right now
        self.activity = None
        self.category = None
        self.description = None
        self.tags = []
        self.start_time = None
        self.end_time = None
        self.id = id
        self.ponies = False
        self.delta = delta
        self.activity_id = activity_id

        phase = "start_time" if date else "date"
        for key, val in parse_fact(activity, phase, {}, date).iteritems():
            setattr(self, key, val)

        # override implicit with explicit
        self.category = (category.replace(",", "").strip() or
                         (self.category and self.category.strip()))
        self.description = (description or self.description or "").strip() or None
        self.tags =  tags or self.tags or []
        self.start_time = start_time or self.start_time or None
        self.end_time = end_time or self.end_time or None


    # TODO: __iter__ seems to never be used => to remove ?
    def __iter__(self):
        date = self.date
        keys = {
            'id': int(self.id) if self.id else "",
            'activity': self.activity,
            'category': self.category,
            'description': self.description,
            'tags': [tag.encode("utf-8").strip() for tag in self.tags],
            'date': calendar.timegm(date.timetuple()) if date else "",
            'start_time': self.start_time if isinstance(self.start_time, basestring) else calendar.timegm(self.start_time.timetuple()),
            'end_time': self.end_time if isinstance(self.end_time, basestring) else calendar.timegm(self.end_time.timetuple()) if self.end_time else "",
            'delta': self.delta.seconds + self.delta.days * 24 * 60 * 60 if self.delta else "" #duration in seconds
        }
        return iter(keys.items())


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
            self.start_time = hamsterday_time_to_datetime(value, self.start_time.time())
        if self.end_time:
            self.end_time = hamsterday_time_to_datetime(value, self.end_time.time())

    def serialized_name(self):
        res = self.activity

        if self.category:
            res += "@%s" % self.category

        if self.description or self.tags:
            res += " %s, %s" % (" ".join(["#%s" % tag for tag in self.tags]),
                               self.description or "")
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
        return "%s %s" % (datetime, name)


    def __str__(self):
        return self.serialized_time(prepend_date=True)




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
    now = dt.datetime.now()

    # determine what we can look for
    phases = [
        "date",  # hamster day
        "start_time",
        "end_time",
        "tags",
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
            date = now.date()
            remaining_text = text
        return parse_fact(remaining_text, "start_time", res, date)

    if "start_time" in phases or "end_time" in phases:
        # looking for start or end time

        delta_re = re.compile("^-[0-9]{1,3}$")
        time_re = re.compile("^([0-1]?[0-9]|[2][0-3]):([0-5][0-9])$")
        time_range_re = re.compile("^([0-1]?[0-9]|[2][0-3]):([0-5][0-9])-([0-1]?[0-9]|[2][0-3]):([0-5][0-9])$")

        if delta_re.match(fragment):
            # TODO untested
            # delta_re was probably thought to be used
            # alone or together with a start_time
            # but using "now" prevents the latter
            res[phase] = now + dt.timedelta(minutes=int(fragment))
            remaining_text = remove_fragment(text, fragment)
            return parse_fact(remaining_text, phases[phases.index(phase)+1], res, date)

        elif time_re.match(fragment):
            time = dt.datetime.strptime(fragment, TIME_FMT).time()
            res[phase] = hamsterday_time_to_datetime(date, time)
            remaining_text = remove_fragment(text, fragment)
            return parse_fact(remaining_text, phases[phases.index(phase)+1], res, date)

        elif time_range_re.match(fragment) and phase == "start_time":
            start, end = fragment.split("-")
            start_time = dt.datetime.strptime(start, TIME_FMT).time()
            end_time = dt.datetime.strptime(end, TIME_FMT).time()
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
            m = re.search(tag_re, remaining_text)
            if not m:
                break
            tag = m.group(1)
            tags.append(tag)
            # strip the matched string (including #)
            remaining_text = remaining_text[:m.start()]
        res["tags"] = tags
        return parse_fact(remaining_text, "activity", res, date)

    if "activity" in phases:
        activity = re.split("[@|#|,]", text, 1)[0]
        if looks_like_time(activity):
            # want meaningful activities
            return res

        res["activity"] = activity
        remaining_text = remove_fragment(text, activity)
        return parse_fact(remaining_text, "category", res, date)

    if "category" in phases:
        category, _, description = text.partition(",")
        res["category"] = category.lstrip("@").strip() or None
        res["description"] = description.strip() or None
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
