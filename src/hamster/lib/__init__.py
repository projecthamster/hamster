import calendar
import datetime as dt
import logging
import re

DATE_FMT = "%d-%m-%Y"
TIME_FMT = "%H:%M"

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
            activity = str(initial_fact)

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

        for key, val in parse_fact(activity).iteritems():
            setattr(self, key, val)


        # override implicit with explicit
        self.category = category.replace(",", "") or self.category or None
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
        """hamster day."""
        # FIXME: should take into account the day start. cf. db.py, __get_todays_facts
        #        there should be a common function in lib
        return self.start_time.date()


    def serialized_name(self):
        res = self.activity

        if self.category:
            res += "@%s" % self.category

        if self.description or self.tags:
            res += "%s, %s" % (" ".join(["#%s" % tag for tag in self.tags]),
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
    

    def __str__(self):
        return "%s %s" % (self.serialized_time(), self.serialized_name())




def parse_fact(text, phase=None, res=None, date=None):
    """tries to extract fact fields from the string
        the optional arguments in the syntax makes us actually try parsing
        values and fallback to next phase
        start -> [end] -> activity[@category] -> tags

        Returns dict for the fact and achieved phase

        TODO - While we are now bit cooler and going recursively, this code
        still looks rather awfully spaghetterian. What is the real solution?
        
        Tentative syntax:
        [date] start_time[-end_time] activity[@category][, description]{ #tag}
    """
    now = dt.datetime.now()

    # determine what we can look for
    phases = [
        "date",
        "start_time",
        "end_time",
        "activity",
        "category",
        "tags",
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
            res[phase] = dt.datetime.combine(date, dt.datetime.strptime(fragment, TIME_FMT).time())
            remaining_text = remove_fragment(text, fragment)
            return parse_fact(remaining_text, phases[phases.index(phase)+1], res, date)

        elif time_range_re.match(fragment) and phase == "start_time":
            start, end = fragment.split("-")
            # FIXME: both should take into account the day start. cf. db.py, __get_todays_facts
            res["start_time"] = dt.datetime.combine(date, dt.datetime.strptime(start, TIME_FMT).time())
            res["end_time"] = dt.datetime.combine(date, dt.datetime.strptime(end, TIME_FMT).time())
            remaining_text = remove_fragment(text, fragment)
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
        category = re.split("[#|,]", text, 1)[0]
        if category.lstrip().startswith("@"):
            res["category"] = category.lstrip("@ ")
            remaining_text = remove_fragment(text, category)
            return parse_fact(remaining_text, "tags", res, date)

        return parse_fact(text, "tags", res, date)

    if "tags" in phases:
        tags, desc = text.split(",", 1) if "," in text else (text, None)

        tags = [tag.strip() for tag in re.split("[#]", tags) if tag.strip()]
        if tags:
            res["tags"] = tags

        if (desc or "").strip():
            res["description"] = desc.strip()

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
