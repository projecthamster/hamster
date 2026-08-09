# - coding: utf-8 -

# Copyright (C) 2007-2009 Toms Bauģis <toms.baugis at gmail.com>

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

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import Pango as pango

from hamster.lib import datetime as dt
# import our children
from hamster.widgets.activityentry import (
    ActivityEntry,
    CategoryEntry,
    CmdLineEntry,
    )
from hamster.widgets.timeinput import TimeInput
from hamster.widgets.dayline import DayLine
from hamster.widgets.tags import Tag, TagBox, TagsEntry
from hamster.widgets.reportchooserdialog import ReportChooserDialog
from hamster.widgets.facttree import FactTree
from hamster.widgets.dates import Calendar, RangePick


# handy wrappers
def add_hint(entry, hint):
    entry.set_placeholder_text(hint)
