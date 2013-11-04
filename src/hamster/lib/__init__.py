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
    
    STRINGFORMAT = "%d-%m-%Y %H:%M"
    TIMESTRINGFORMAT = "%H:%M"
    
    #TODO: Change attribute name for id.
    def __init__(self, activity, category = "", description = "", tags = "",
                 start_time = None, end_time = None, id = None, delta = None,
                 date = None, activity_id = None, exported = False):
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
        self.date = date #TODO: Where is this used???
        self.activity_id = activity_id
        self.exported = exported

        # parse activity
        input_parts = activity.strip().split(" ")
        if len(input_parts) > 1 and re.match('^-?\d', input_parts[0]): #look for time only if there is more
            potential_time = activity.split(" ")[0]
            potential_end_time = None
            if len(potential_time) > 1 and  potential_time.startswith("-"):
                #if starts with minus, treat as minus delta minutes
                self.start_time = dt.datetime.now() + dt.timedelta(minutes = int(potential_time))

            else:
                if potential_time.find("-") > 0:
                    potential_time, potential_end_time = potential_time.split("-", 1)
                    self.end_time = figure_time(potential_end_time)

                self.start_time = figure_time(potential_time)

            #remove parts that worked
            if self.start_time and potential_end_time and not self.end_time:
                self.start_time = None #scramble
            elif self.start_time:
                activity = activity[activity.find(" ")+1:]

        #see if we have description of activity somewhere here (delimited by comma)
        if activity.find(",") > 0:
            activity, self.description = activity.split(",", 1)

            if " #" in self.description:
                self.description, self.tags = self.description.split(" #", 1)
                self.tags = [tag.strip(", ") for tag in self.tags.split("#") if tag.strip(", ")]

            self.description = self.description.strip()

        if activity.find("@") > 0:
            activity, self.category = activity.split("@", 1)
            self.category = self.category.strip()

        #this is most essential
        if any([b in activity for b in ("bbq", "barbeque", "barbecue")]) and "omg" in activity:
            self.ponies = True
            self.description = "[ponies = 1], [rainbows = 0]"

        #only thing left now is the activity name itself
        self.activity = activity.strip()

        tags = tags or ""
        if tags and isinstance(tags, basestring):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # override implicit with explicit
        self.category = category.replace(",", "") or self.category or None
        self.description = (description or "").replace(" #", " ") or self.description or None
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
            res += ",%s %s" % (self.description or "",
                               " ".join(["#%s" % tag for tag in self.tags]))
            #TODO: Fix spacing after comma in ,%s...; does not match freeform
        return res
    
    def serialized_name_for_menu(self):
        res = ""
            
        res += self.activity

        if self.description or self.tags:
            res += ",%s %s" % (self.description or "",
                               " ".join(["#%s" % tag for tag in self.tags]))
        
        res += self.start_time.strftime(" (%d.%m %H:%M)")
        
        return res

    def __str__(self):
        time = ""
        if self.start_time:
            time = self.start_time.strftime(self.STRINGFORMAT)
        if self.end_time:
            time = "%s - %s" % (time, self.end_time.strftime(self.TIMESTRINGFORMAT))
        return "%s %s" % (time, self.serialized_name())
