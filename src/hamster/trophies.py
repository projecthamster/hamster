# - coding: utf-8 -

# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.

"""Deal with trophies if there.
   For now the trophy configuration of hamster reside in gnome-achievements, in
   github:
   http://github.com/tbaugis/gnome-achievements/blob/master/data/achievements/hamster-applet.trophies.xml
   Eventually they will move into hamster.
"""

try:
    from gnome_achievements import client as trophies_client
    storage = trophies_client.Storage()
except:
    storage = None

import stuff
import datetime as dt

def unlock(achievement_id):
    if not storage: return
    storage.unlock_achievement("hamster-applet", achievement_id)

def check(achievement_id):
    if not storage: return None
    return storage.check_achievement("hamster-applet", achievement_id)

def increment(counter_id, context = ""):
    if not storage: return 0
    return storage.increment_counter("hamster-applet", counter_id, context)

class Checker(object):
    def __init__(self):
        # use runtime flags where practical
        self.flags = {}


    def check_today(self, facts):
        if not storage: return

        for fact in facts[-2:]: # consider just the last two current ongoing and the previous one
            # in_the_zone - spent 6 hours on single activity
            if fact['end_time'] and fact['end_time'] - fact['start_time'] > dt.timedelta(hours = 6):
                unlock("in_the_zone")

            # insomnia - finish activity in a new day
            if (fact['end_time'] and fact['start_time'].date() != fact['end_time'].date()) or \
               (fact['end_time'] is None and fact['start_time'].date() != dt.date.today()):
                unlock("insomnia")

        # overwhelmed: tracking for more than 16 hours during one da
        total = stuff.duration_minutes([fact['delta'] for fact in facts])
        if total > 16 * 60:
            unlock("overwhelmed")


    def check_update_based(self, prev_id, new_id, activity_name, tags, start_time, end_time, category_name, description):
        if not storage: return

        if not self.flags.get('last_update_id') or prev_id != self.flags['last_update_id']:
            self.flags['same_updates_in_row'] = 0
        elif self.flags['last_update_id'] == prev_id:
            self.flags['same_updates_in_row'] +=1
        self.flags['last_update_id'] = new_id


        # all wrong – edited same activity 5 times in a row
        if self.flags['same_updates_in_row'] == 5:
            unlock("all_wrong")


    def check_fact_based(self, activity_name, tags, start_time, end_time, category_name, description):
        """quite possibly these all could be called from the service as
           there is bigger certainty as to what did actually happen"""

        # checks fact based trophies
        if not storage: return

        # explicit over implicit
        fact = stuff.parse_activity_input(activity_name)
        if not fact.activity_name:  # TODO - parse_activity could return None for these cases
            return

        # full plate - use all elements of syntax parsing
        if all((fact.category_name, fact.description, fact.tags, fact.start_time, fact.end_time)):
            unlock("full_plate")


        fact.tags = [tag.strip() for tag in tags.split(",") if tag.strip()] or fact.tags
        fact.category_name = category_name or fact.category_name
        fact.description = description or fact.description
        fact.start_time = start_time or fact.start_time or dt.datetime.now()
        fact.end_time = end_time or fact.end_time


        # Jumper - hidden - made 10 switches within an hour (radical)
        if not fact.end_time: #end time normally denotes switch
            last_ten = self.flags.setdefault('last_ten_ongoing', [])
            last_ten.append(fact)
            last_ten = last_ten[-10:]

            if len(last_ten) == 10 and (last_ten[-1].start_time - last_ten[0].start_time) <= dt.timedelta(hours=1):
                unlock("jumper")

        # good memory - entered three past activities during a day
        if fact.end_time and fact.start_time.date() == dt.date.today():
            good_memory = increment("past_activities", dt.date.today().strftime("%Y%m%d"))
            if good_memory == 3:
                unlock("good_memory")

        # layering - entered 4 activities in a row in one of previous days, each one overlapping the previous one
        #            avoiding today as in that case the layering
        last_four = self.flags.setdefault('last_four', [])
        last_four.append(fact)
        last_four = last_four[-4:]
        if len(last_four) == 4:
            layered = True
            for prev, next in zip(last_four, last_four[1:]):
                if next.start_time.date == dt.date.today() or \
                   next.start_time < prev.start_time or \
                   (prev.end_time and prev.end_time < next.start_time):
                    layered = False

            if layered:
                unlock("layered")

        # wait a minute! - Switch to a new activity within 60 seconds
        if len(last_four) >= 2:
            prev, next = last_four[-2:]
            if prev.end_time is None and next.end_time is None and (next.start_time - prev.start_time) < dt.timedelta(minutes = 1):
                unlock("wait_a_minute")


        # alpha bravo charlie – used delta times to enter at least 50 activities
        if fact.start_time and activity_name.startswith("-"):
            counter = increment("hamster-applet", "alpha_bravo_charlie")
            if counter == 50:
                unlock("alpha_bravo_charlie")


        # cryptic - hidden - used word shorter than 4 letters for the activity name
        if len(fact.activity_name) < 4:
            unlock("cryptic")

        # madness – hidden – entered an activity in all caps
        if fact.activity_name == fact.activity_name.upper():
            unlock("madness")

        # verbose - hidden - description longer than 5 words
        if fact.description and len([word for word in fact.description.split(" ") if len(word.strip()) > 2]) >= 5:
            unlock("verbose")

        # overkill - used 8 or more tags on a single activity
        if len(fact.tags) >=8:
            unlock("overkill")

        # ponies - hidden - discovered the ponies
        if fact.ponies:
            unlock("ponies")


        # TODO - after the trophies have been unlocked there is not much point in going on
        #        patrys complains about who's gonna garbage collect. should think
        #        about this
        if not storage.check_achievement("hamster-applet", "ultra_focused"):
            activity_count = increment("hamster-applet", "focused_%s@%s" % (fact.activity_name, fact.category_name or ""))
            # focused – 100 facts with single activity
            if activity_count == 100:
                unlock("hamster-applet", "focused")

            # ultra focused – 500 facts with single activity
            if activity_count == 500:
                unlock("hamster-applet", "ultra_focused")


checker = Checker()
