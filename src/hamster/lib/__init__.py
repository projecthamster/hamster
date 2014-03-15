import calendar
import datetime as dt
import re

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
    def __init__(self, activity, category = "", description = "", tags = "",
                 start_time = None, end_time = None, id = None, delta = None,
                 date = None, activity_id = None):
        """the category, description and tags can be either passed in explicitly
        or by using the "activity@category, description #tag #tag" syntax.
        explicitly stated values will take precedence over derived ones"""
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
        self.date = date
        self.activity_id = activity_id

        for key, val in parse_fact(activity).iteritems():
            setattr(self, key, val)


        # override implicit with explicit
        self.category = category.replace(",", "") or self.category or None
        self.description = (description or self.description or "").strip() or None
        self.tags =  tags or self.tags or []
        self.start_time = start_time or self.start_time or None
        self.end_time = end_time or self.end_time or None


    def __iter__(self):
        keys = {
            'id': int(self.id) if self.id else "",
            'activity': self.activity,
            'category': self.category,
            'description': self.description,
            'tags': [tag.encode("utf-8").strip() for tag in self.tags],
            'date': calendar.timegm(self.date.timetuple()) if self.date else "",
            'start_time': self.start_time if isinstance(self.start_time, basestring) else calendar.timegm(self.start_time.timetuple()),
            'end_time': self.end_time if isinstance(self.end_time, basestring) else calendar.timegm(self.end_time.timetuple()) if self.end_time else "",
            'delta': self.delta.seconds + self.delta.days * 24 * 60 * 60 if self.delta else "" #duration in seconds
        }
        return iter(keys.items())


    def serialized_name(self):
        res = self.activity

        if self.category:
            res += "@%s" % self.category

        if self.description or self.tags:
            res += "%s, %s" % (" ".join(["#%s" % tag for tag in self.tags]),
                               self.description or "")
        return res

    def __str__(self):
        time = ""
        if self.start_time:
            time = self.start_time.strftime("%d-%m-%Y %H:%M")
        if self.end_time:
            time = "%s - %s" % (time, self.end_time.strftime("%H:%M"))
        return "%s %s" % (time, self.serialized_name())




def parse_fact(text, phase=None):
    """tries to extract fact fields from the string
        the optional arguments in the syntax makes us actually try parsing
        values and fallback to next phase
        start -> [end] -> activity[@category] -> tags

        Returns dict for the fact and achieved phase

        TODO - While we are now bit cooler and going recursively, this code
        still looks rather awfully spaghetterian. What is the real solution?
    """
    now = dt.datetime.now()

    # determine what we can look for
    phases = [
        "start_time",
        "end_time",
        "activity",
        "category",
        "tags",
    ]

    phase = phase or phases[0]
    phases = phases[phases.index(phase):]
    res = {}

    text = text.strip()
    if not text:
        return {}

    fragment = re.split("[\s|#]", text, 1)[0].strip()

    def next_phase(fragment, phase):
        res.update(parse_fact(text[len(fragment):], phase))
        return res

    if "start_time" in phases or "end_time" in phases:
        # looking for start or end time

        delta_re = re.compile("^-[0-9]{1,3}$")
        time_re = re.compile("^([0-1]?[0-9]|[2][0-3]):([0-5][0-9])$")
        time_range_re = re.compile("^([0-1]?[0-9]|[2][0-3]):([0-5][0-9])-([0-1]?[0-9]|[2][0-3]):([0-5][0-9])$")

        if delta_re.match(fragment):
            res[phase] = now + dt.timedelta(minutes=int(fragment))
            return next_phase(fragment, phases[phases.index(phase)+1])

        elif time_re.match(fragment):
            res[phase] = dt.datetime.combine(now.date(), dt.datetime.strptime(fragment, "%H:%M").time())
            return next_phase(fragment, phases[phases.index(phase)+1])

        elif time_range_re.match(fragment) and phase == "start_time":
            start, end = fragment.split("-")
            res["start_time"] = dt.datetime.combine(now.date(), dt.datetime.strptime(start, "%H:%M").time())
            res["end_time"] = dt.datetime.combine(now.date(), dt.datetime.strptime(end, "%H:%M").time())
            phase = "activity"
            return next_phase(fragment, "activity")

    if "activity" in phases:
        activity = re.split("[@|#|,]", text, 1)[0]
        if looks_like_time(activity):
            # want meaningful activities
            return res

        res["activity"] = activity
        return next_phase(activity, "category")

    if "category" in phases:
        category = re.split("[#|,]", text, 1)[0]
        if category.lstrip().startswith("@"):
            res["category"] = category.lstrip("@ ")
            return next_phase(category, "tags")

        return next_phase("", "tags")

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
