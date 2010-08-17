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
except:
    trophies_client = None

import stuff

class Checker(object):
    def __init__(self):
        self.storage = None
        if trophies_client:
            self.trophies = trophies_client.Storage()



    def check_fact_based(self, activity_name, tags, start_time, end_time, category_name, description):
        # checks fact based trophies
        if not self.trophies: return

        # explicit over implicit
        fact = stuff.parse_activity_input(activity_name)
        if not fact.activity_name:  # TODO - parse_activity could return None for these cases
            return

        # full plate - use all elements of syntax parsing
        if all((fact.category_name, fact.description, fact.tags, fact.start_time, fact.end_time)):
            self.trophies.unlock_achievement("hamster-applet", "full_plate")


        fact.tags = [tag.strip() for tag in tags.split(",") if tag.strip()] or fact.tags
        fact.category_name = category_name or fact.category_name
        fact.description = description or fact.description
        fact.start_time = start_time or fact.start_time
        fact.end_time = end_time or fact.end_time



        # cryptic - hidden - used word shorter than 4 letters for the activity name
        if len(fact.activity_name) < 4:
            self.trophies.unlock_achievement("hamster-applet", "cryptic")

        # madness – hidden – entered an activity in all caps
        if fact.activity_name == fact.activity_name.upper():
            self.trophies.unlock_achievement("hamster-applet", "madness")

        # verbose - hidden - description longer than 5 words
        if fact.description and len((word for word in fact.description.split(" ") if word.strip())) >= 5:
            self.trophies.unlock_achievement("hamster-applet", "verbose")

        # overkill - used 8 or more tags on a single activity
        if len(fact.tags) >=8:
            self.trophies.unlock_achievement("hamster-applet", "overkill")

checker = Checker()
