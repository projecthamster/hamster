# - coding: utf-8 -

# Copyright (C) 2008-2009 Toms Bauģis <toms.baugis at gmail.com>

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

import logging

MAX_USER_SUGGESTIONS = 10
logger = logging.getLogger(__name__)   # noqa: E402

import bisect
import cairo
import re

from xml.sax.saxutils import escape
from gi.repository import Gdk as gdk
from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject
from gi.repository import PangoCairo as pangocairo
from gi.repository import Pango as pango
from collections import defaultdict
from copy import deepcopy

from hamster import client
from hamster.lib import datetime as dt
from hamster.lib import stuff
from hamster.lib import graphics
from hamster.lib.configuration import runtime
from hamster.lib.fact import Fact


# note: Still experimenting in this module.
#       Code redundancy to be removed later.


def extract_search(text):
    fact = Fact.parse(text)
    search = fact.activity
    if fact.category:
        search += "@%s" % fact.category
    if fact.tags:
        search += " #%s" % (" #".join(fact.tags))
    return search.lower()

def extract_search_without_tags_and_category(text):
    fact = Fact.parse(text)
    search = fact.activity
    return search.lower()

class DataRow(object):
    """want to split out visible label, description, activity data
      and activity data with time (full_data)"""
    def __init__(self, label, data=None, full_data=None, description=None):
        self.label = label
        self.data = data or label
        self.full_data = full_data or data or label
        self.description = description or ""

class Label(object):
    """a much cheaper label that would be suitable for cellrenderer"""
    def __init__(self, x=0, y=0):
        self.x, self.y = x, y
        self._label_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
        self.layout = pangocairo.create_layout(self._label_context)
        self.layout.set_font_description(pango.FontDescription(graphics._font_desc))
        self.layout.set_markup("Hamster") # dummy
        self.height = self.layout.get_pixel_size()[1]

    def show(self, g, text, color=None):
        g.move_to(self.x, self.y)

        self.layout.set_markup(text)
        g.save_context()
        if color:
            g.set_color(color)
        pangocairo.show_layout(g.context, self.layout)
        g.restore_context()


class CompleteTree(graphics.Scene):
    """
    ASCII Art

    | Icon | Activity - description |

    """

    __gsignals__ = {
        # enter or double-click, passes in current day and fact
        'on-select-row': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }


    def __init__(self):
        graphics.Scene.__init__(self, style_class=gtk.STYLE_CLASS_VIEW)

        self.set_can_focus(False)

        self.row_positions = []

        self.current_row = None
        self.rows = []

        self.style = self._style

        self.label = Label(x=5, y=3)
        self.row_height = self.label.height + 10

        self.connect("on-key-press", self.on_key_press)
        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-mouse-down", self.on_mouse_down)

    def _get_mouse_row(self, event):
        hover_row = None
        for row, y in zip(self.rows, self.row_positions):
            if y <= event.y <= (y + self.row_height):
                hover_row = row
                break
        return hover_row

    def on_mouse_move(self, scene, event):
        row = self._get_mouse_row(event)
        if row:
            self.current_row = row
            self.redraw()

    def on_mouse_down(self, scene, event):
        row = self._get_mouse_row(event)
        if row:
            self.set_current_row(self.rows.index(row))

    def on_key_press(self, scene, event):
        if event.keyval == gdk.KEY_Up:
            idx = self.rows.index(self.current_row) if self.current_row else 1
            self.set_current_row(idx - 1)

        elif event.keyval == gdk.KEY_Down:
            idx = self.rows.index(self.current_row) if self.current_row else -1
            self.set_current_row(idx + 1)

    def set_current_row(self, idx):
        idx = max(0, min(len(self.rows) - 1, idx))
        row = self.rows[idx]
        self.current_row = row
        self.redraw()
        self.emit("on-select-row", row)

    def set_rows(self, rows):
        self.current_row = None
        self.rows = rows
        self.set_row_positions()

    def set_row_positions(self):
        """creates a list of row positions for simpler manipulation"""
        self.row_positions = [i * self.row_height for i in range(len(self.rows))]
        self.set_size_request(0, self.row_positions[-1] + self.row_height if self.row_positions else 0)

    def on_enter_frame(self, scene, context):
        if not self.height:
            return

        colors = {
            "normal": self.style.get_color(gtk.StateFlags.NORMAL),
            "normal_bg": self.style.get_background_color(gtk.StateFlags.NORMAL),
            "selected": self.style.get_color(gtk.StateFlags.SELECTED),
            "selected_bg": self.style.get_background_color(gtk.StateFlags.SELECTED),
        }

        g = graphics.Graphics(context)
        g.set_line_style(1)
        g.translate(0.5, 0.5)


        for row, y in zip(self.rows, self.row_positions):
            g.save_context()
            g.translate(0, y)

            color, bg = colors["normal"], colors["normal_bg"]
            if row == self.current_row:
                color, bg = colors["selected"], colors["selected_bg"]
                g.fill_area(0, 0, self.width, self.row_height, bg)

            label = row.label
            if row.description:
                description_color = graphics.Colors.mix(bg, color, 0.75)
                description_color_str = graphics.Colors.hex(description_color)

                label = '{}  <span color="{}">[{}]</span>'.format(label,
                                                                  description_color_str,
                                                                  row.description)

            self.label.show(g, label, color=color)

            g.restore_context()



class CmdLineEntry(gtk.Entry):
    def __init__(self, updating=True, **kwargs):
        gtk.Entry.__init__(self, **kwargs)

        # default day for times without date
        self.default_day = None

        # to be set by the caller, if editing an existing fact
        self.original_fact = None

        self.popup = gtk.Window(type = gtk.WindowType.POPUP)
        self.popup.set_type_hint(gdk.WindowTypeHint.COMBO)  # why not
        self.popup.set_attached_to(self)  # attributes
        self.popup.set_transient_for(self.get_ancestor(gtk.Window))  # position

        box = gtk.Frame()
        box.set_shadow_type(gtk.ShadowType.IN)
        self.popup.add(box)

        self.complete_tree = CompleteTree()
        self.tree_checker = self.complete_tree.connect("on-select-row", self.on_tree_select_row)
        self.complete_tree.connect("on-click", self.on_tree_click)
        box.add(self.complete_tree)

        self.storage = client.Storage()
        self.todays_facts = None
        self.local_suggestions = None
        self.load_suggestions()

        self.ext_suggestions = []
        self.ext_suggestion_filler_timer = gobject.timeout_add(0, self.__refresh_ext_suggestions, "")

        self.ignore_stroke = False

        self.set_icon_from_icon_name(gtk.EntryIconPosition.SECONDARY, "go-down-symbolic")

        self.checker = self.connect("changed", self.on_changed)
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("icon-press", self.on_icon_press)

    def on_changed(self, entry):
        text = self.get_text()

        with self.complete_tree.handler_block(self.tree_checker):
            self.show_suggestions(text)

        if self.ignore_stroke:
            self.ignore_stroke = False
            return

        def complete():
            text, suffix = self.complete_first()
            if suffix:
                #self.ignore_stroke = True
                with self.handler_block(self.checker):
                    self.update_entry("%s%s" % (text, suffix))
                    self.select_region(len(text), -1)
        gobject.timeout_add(0, complete)

    def on_focus_out(self, entry, event):
        self.popup.hide()

    def on_icon_press(self, entry, icon, event):
        if self.popup.get_visible():
            self.popup.hide()
        else:
            self.grab_focus()
            self.show_suggestions(self.get_text())

    def on_key_press(self, entry, event=None):
        if event.keyval in (gdk.KEY_BackSpace, gdk.KEY_Delete):
            self.ignore_stroke = True

        elif event.keyval in (gdk.KEY_Return, gdk.KEY_KP_Enter, gdk.KEY_Escape):
            self.popup.hide()
            self.set_position(-1)

        elif event.keyval in (gdk.KEY_Up, gdk.KEY_Down):
            if not self.popup.get_visible():
                self.show_suggestions(self.get_text())
            self.complete_tree.on_key_press(self, event)
            return True

    def on_tree_click(self, entry, tree, event):
        self.popup.hide()

    def on_tree_select_row(self, tree, row):
        with self.handler_block(self.checker):
            label = row.full_data
            self.update_entry(label)
            self.set_position(-1)

    def __load_ext_suggestions_with_timer(self, query=""):
        if self.ext_suggestion_filler_timer:
            gobject.source_remove(self.ext_suggestion_filler_timer)
        self.ext_suggestion_filler_timer = gobject.timeout_add(1000, self.__refresh_ext_suggestions, extract_search_without_tags_and_category(query))

    def __refresh_ext_suggestions(self, query=""):
        suggestions = []
        facts = self.storage.get_ext_activities(query)
        for fact in facts:
            label = fact.get("name")
            category = fact.get("category")
            if category:
                label += "@%s" % category
            score = 10**10
            suggestions.append((label, score))
        logger.debug("external suggestion refreshed for query: %s" % query)
        self.ext_suggestions = suggestions
        self.update_suggestions(self.get_text())
        self.ext_suggestion_filler_timer = None

    def load_suggestions(self):
        self.todays_facts = self.storage.get_todays_facts()

        # list of facts of last month
        now = dt.datetime.now()
        last_month = self.storage.get_facts(now - dt.timedelta(days=30), now)

        # naive recency and frequency rank
        # score is as simple as you get 30-days_ago points for each occurence
        suggestions = defaultdict(int)
        for fact in last_month:
            days = 30 - (now - dt.datetime.combine(fact.date, dt.time())).total_seconds() / 60 / 60 / 24
            label = fact.activity
            if fact.category:
                label += "@%s" % fact.category

            suggestions[label] += days

            if fact.tags:
                label += " #%s" % (" #".join(fact.tags))
                suggestions[label] += days

        for rec in self.storage.get_activities():
            label = rec["name"]
            if rec["category"]:
                label += "@%s" % rec["category"]
            suggestions[label] += 0

        # list of (label, score), higher scores first
        self.local_suggestions = sorted(suggestions.items(), key=lambda x: x[1], reverse=True)

    def complete_first(self):
        text = self.get_text()
        fact = Fact.parse(text)
        search = extract_search(text)
        if not self.complete_tree.rows or not fact.activity:
            return text, None

        label = self.complete_tree.rows[0].data
        if label.startswith(search):
            return text, label[len(search):]

        return text, None

    def update_entry(self, text):
        self.set_text(text or "")

    def update_suggestions(self, text=""):
        """
            * from previous activity | set time | minutes ago | start now
            * to ongoing | set time

            * activity
            * [@category]
            * #tags, #tags, #tags

            * we will leave description for later

            all our magic is space separated, strictly, start-end can be just dash

            phases:

            [start_time] | [-end_time] | activity | [@category] | [#tag]
        """

        res = []

        fact = Fact.parse(text)
        now = dt.datetime.now()

        # figure out what we are looking for
        # time -> activity[@category] -> tags -> description
        # presence of an attribute means that we are not looking for the previous one
        # we still might be looking for the current one though
        looking_for = "start_time"
        fields = ["start_time", "end_time", "activity", "category", "tags", "description", "done"]
        for field in reversed(fields):
            if getattr(fact, field, None):
                looking_for = field
                if text[-1] == " ":
                    looking_for = fields[fields.index(field)+1]
                break

        fragments = [f for f in re.split("[\s|#]", text)]
        current_fragment = fragments[-1] if fragments else ""

        search = extract_search(text)

        matches = []
        suggestions = self.local_suggestions
        for match, score in suggestions:
            search_words = search.split(" ")
            match_words = match.lower().split(" ")
            if all(search_word in match_words for search_word in search_words):
                if match.lower().startswith(search):
                    score += 10**8 # boost beginnings
                matches.append((match, score))
        for match, score in self.ext_suggestions:
            matches.append((match, score))

        # need to limit these guys, sorry
        matches = sorted(matches, key=lambda x: x[1], reverse=True)[:MAX_USER_SUGGESTIONS]

        for match, score in matches:
            label = (fact.start_time or now).strftime("%H:%M")
            if fact.end_time:
                label += fact.end_time.strftime("-%H:%M")

            markup_label = label + " " + (self.__bold_search(match, search) if search else escape(match))
            label += " " + match

            res.append(DataRow(markup_label, match, label))

        # list of tuples (description, variant)
        variants = []

        variant_fact = None
        if fact.end_time is None:
            description = "stop now"
            variant_fact = fact.copy()
            variant_fact.end_time = now
        elif self.todays_facts and fact == self.todays_facts[-1]:
            # that one is too dangerous, except for the last entry
            description = "keep up"
            # Do not use Fact(..., end_time=None): it would be a no-op
            variant_fact = fact.copy()
            variant_fact.end_time = None

        if variant_fact:
            variant_fact.description = None
            variant = variant_fact.serialized(default_day=self.default_day)
            variants.append((description, variant))

        if fact.start_time is None:
            description = "start now"
            variant = now.strftime("%H:%M ")
            variants.append((description, variant))

            prev_fact = self.todays_facts[-1] if self.todays_facts else None
            if prev_fact and prev_fact.end_time:
                since = (now - prev_fact.end_time).format()
                description = "from previous activity, %s ago" % since
                variant = prev_fact.end_time.strftime("%H:%M ")
                variants.append((description, variant))

            description = "start activity -n minutes ago (1 or 3 digits allowed)"
            variant = "-"
            variants.append((description, variant))

        text = text.strip()
        if text:
            description = "clear"
            variant = ""
            variants.append((description, variant))

        for (description, variant) in variants:
            res.append(DataRow(variant, description=description))

        self.complete_tree.set_rows(res)

    def __bold_search(self, match, search):
        result = escape(match)
        for word in search.split(" "):
            pattern = re.compile("(%s)" % re.escape(word), re.IGNORECASE)
            result = re.sub(pattern, r"<b>\1</b>", result)

        return result

    def show_suggestions(self, text):
        if not self.get_window():
            return

        entry_alloc = self.get_allocation()
        entry_x, entry_y = self.get_window().get_origin()[1:]
        x, y = entry_x + entry_alloc.x, entry_y + entry_alloc.y + entry_alloc.height

        self.popup.show_all()
        self.__load_ext_suggestions_with_timer(text)
        self.update_suggestions(text)

        tree_w, tree_h = self.complete_tree.get_size_request()

        self.popup.move(x, y)
        self.popup.resize(entry_alloc.width, tree_h)
        self.popup.show_all()


class ActivityEntry():
    """Activity entry widget.

    widget (gtk.Entry): the associated activity entry
    category_widget (gtk.Entry): the associated category entry
    """
    def __init__(self, widget=None, category_widget=None, **kwds):
        # widget and completion may be defined already
        # e.g. in the glade edit_activity.ui file
        self.widget = widget
        if not self.widget:
            self.widget = gtk.Entry(**kwds)

        self.category_widget = category_widget

        # internal list of actions added to the suggestions
        self._action_list = []
        self.completion = self.widget.get_completion()
        if not self.completion:
            self.completion = gtk.EntryCompletion()
            self.widget.set_completion(self.completion)

        # text to display/filter on, activity, category
        self.text_column = 0
        self.activity_column = 1
        self.category_column = 2

        # whether the category choice limit the activity suggestions
        self.filter_on_category = True if self.category_widget else False
        self.model = gtk.ListStore(str, str, str)
        self.completion.set_model(self.model)
        self.completion.set_text_column(self.text_column)
        self.completion.set_match_func(self.match_func, None)
        # enable selection with up and down arrow
        self.completion.set_inline_selection(True)
        # It is not possible to change actions later dynamically;
        # once actions are removed,
        # they can not be added back (they are not visible).
        # => nevermind, showing all actions.
        self.add_action("show all", "Show all activities")
        self.add_action("filter on category", "Filter on selected category")

        self.connect("icon-release", self.on_icon_release)
        self.connect("focus-in-event", self.on_focus_in_event)
        self.completion.connect('match-selected', self.on_match_selected)
        self.completion.connect("action_activated", self.on_action_activated)

    def add_action(self, name, text):
        """Add an action to the suggestions.

        name (str): unique label, use to retrieve the action index.
        text (str): text used to display the action.
        """
        markup = "<i>{}</i>".format(stuff.escape_pango(text))
        idx = len(self._action_list)
        self.completion.insert_action_markup(idx, markup)
        self._action_list.append(name)

    def clear(self, notify=True):
        self.widget.set_text("")
        if notify:
            self.emit("changed")

    def match_func(self, completion, key, iter, *user_data):
        if not key.strip():
            # show all keys if entry is empty
            return True
        else:
            # return whether the entered string is
            # anywhere in the first column data
            stripped_key = key.strip()
            activities = self.model.get_value(iter, self.activity_column).lower()
            categories = self.model.get_value(iter, self.category_column).lower()
            key_in_activity = stripped_key in activities
            key_in_category = stripped_key in categories
            return key_in_activity or key_in_category

    def on_action_activated(self, completion, index):
        name = self._action_list[index]
        if name == "clear":
            self.clear(notify=False)
        elif name == "show all":
            self.filter_on_category = False
            self.populate_completions()
        elif name == "filter on category":
            self.filter_on_category = True
            self.populate_completions()

    def on_focus_in_event(self, widget, event):
        self.populate_completions()

    def on_icon_release(self, entry, icon_pos, event):
        self.grab_focus()
        self.set_text("")
        self.emit("changed")

    def on_match_selected(self, entry, model, iter):
        activity_name = model[iter][self.activity_column]
        category_name = model[iter][self.category_column]
        combined = model[iter][self.text_column]
        if self.category_widget:
            self.set_text(activity_name)
            if not self.filter_on_category:
                self.category_widget.set_text(category_name)
        else:
            self.set_text(combined)
        return True  # prevent the standard callback from overwriting text

    def populate_completions(self):
        self.model.clear()
        if self.filter_on_category:
            category_names = [self.category_widget.get_text()]
        else:
            category_names = [category['name']
                              for category in runtime.storage.get_categories()]
        for category_name in category_names:
            category_id = runtime.storage.get_category_id(category_name)
            activities = runtime.storage.get_category_activities(category_id)
            for activity in activities:
                activity_name = activity["name"]
                text = "{}@{}".format(activity_name, category_name)
                self.model.append([text, activity_name, category_name])

    def __getattr__(self, name):
        return getattr(self.widget, name)


class CategoryEntry():
    """Category entry widget.

    widget (gtk.Entry): the associated category entry
    """
    def __init__(self, widget=None, **kwds):
        # widget and completion are already defined
        # e.g. in the glade edit_activity.ui file
        self.widget = widget
        if not self.widget:
            self.widget = gtk.Entry(**kwds)

        self.completion = self.widget.get_completion()
        if not self.completion:
            self.completion = gtk.EntryCompletion()
            self.widget.set_completion(self.completion)
        self.completion.insert_action_markup(0, "<i>Clear ({})</i>".format(_("Unsorted")))
        self.unsorted_action_index = 0

        self.model = gtk.ListStore(str)
        self.completion.set_model(self.model)
        self.completion.set_text_column(0)
        self.completion.set_match_func(self.match_func, None)

        self.widget.connect("icon-release", self.on_icon_release)
        self.widget.connect("focus-in-event", self.on_focus_in_event)
        self.completion.connect("action_activated", self.on_action_activated)

    def clear(self, notify=True):
        self.widget.set_text("")
        if notify:
            self.emit("changed")

    def match_func(self, completion, key, iter, *user_data):
        if not key.strip():
            # show all keys if entry is empty
            return True
        else:
            # return whether the entered string is
            # anywhere in the first column data
            return key.strip() in self.model.get_value(iter, 0).lower()

    def on_action_activated(self, completion, index):
        if index == self.unsorted_action_index:
            self.clear(notify=False)

    def on_focus_in_event(self, widget, event):
        self.populate_completions()

    def on_icon_release(self, entry, icon_pos, event):
        self.widget.grab_focus()
        # do not emit changed on the primary (clear) button
        self.clear()

    def populate_completions(self):
        self.model.clear()
        for category in runtime.storage.get_categories():
            self.model.append([category['name']])

    def __getattr__(self, name):
        return getattr(self.widget, name)
