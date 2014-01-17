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

import gtk, gobject, pango
import datetime as dt
import re

from ..configuration import runtime, conf
from ..lib import Fact, stuff, graphics
from .. import external
from ..lib.rt import TICKET_NAME_REGEX

class ActivityEntry(gtk.Entry):
    __gsignals__ = {
        'value-entered': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self):
        gtk.Entry.__init__(self)
        self.news = False
        self.activities = None
        self.external_activities = [] # suggestions from outer space
        self.categories = None
        self.filter = None
        self.timeout_id = None
        self.max_results = 10 # limit popup size to 10 results
        self.external = external.ActivitiesSource()

        self.popup = gtk.Window(type = gtk.WINDOW_POPUP)

        box = gtk.ScrolledWindow()
        box.set_shadow_type(gtk.SHADOW_IN)
        box.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        self.tree = gtk.TreeView()
        self.tree.set_headers_visible(False)
        self.tree.set_hover_selection(True)

        self.time_icon_cell = gtk.CellRendererPixbuf()
        self.time_icon_cell.set_property("icon-name", "appointment-new")

        self.time_icon_column = gtk.TreeViewColumn("", self.time_icon_cell)
        self.tree.append_column(self.time_icon_column)

        self.time_cell = gtk.CellRendererText()
        self.time_cell.set_property("scale", 0.8)

        self.time_column = gtk.TreeViewColumn("Time",
                                              self.time_cell,
                                              text = 3)
        self.tree.append_column(self.time_column)


        self.activity_column = gtk.TreeViewColumn("Activity",
                                                  gtk.CellRendererText(),
                                                  text=1)
        self.activity_column.set_expand(True)
        self.tree.append_column(self.activity_column)

        self.category_column = gtk.TreeViewColumn("Category",
                                                  gtk.CellRendererText(),
                                                  text=2)
        self.tree.append_column(self.category_column)



        self.tree.connect("button-press-event", self._on_tree_button_press_event)

        box.add(self.tree)
        self.popup.add(box)

        self.connect("button-press-event", self._on_button_press_event)
        self.connect("key-press-event", self._on_key_press_event)
        self.connect("key-release-event", self._on_key_release_event)
        self.connect("focus-out-event", self._on_focus_out_event)
        self.connect("changed", self._on_text_changed)
        self._parent_click_watcher = None # bit lame but works

        self.external_listeners = [
            (runtime.storage, runtime.storage.connect('activities-changed',self.after_activity_update)),
        ]

        self.show()
        self.populate_suggestions()

        self.connect("destroy", self.on_destroy)

    def on_destroy(self, window):
        for obj, handler in self.external_listeners:
            obj.disconnect(handler)

        self.popup.destroy()
        self.popup = None

    def get_value(self):
        activity_name = self.get_text().decode("utf-8").strip()
        if not activity_name:
            return None, False

        # see if entered text matches something from the outer suggestions
        # only consequence of if it does is that it will not attempt to
        # resurrect the activity if it's deleted (hidden)
        # thus avoiding polluting our local suggestions
        external_names = set()
        for activity in self.external_activities:
            name = activity['name']
            if activity['category']:
                name = "%s@%s" % (name, activity['category'])
            external_names.add(name.lower())

        return activity_name, activity_name in external_names

    def hide_popup(self):
        if self._parent_click_watcher and self.get_toplevel().handler_is_connected(self._parent_click_watcher):
            self.get_toplevel().disconnect(self._parent_click_watcher)
            self._parent_click_watcher = None
        if self.timeout_id:
            gobject.source_remove(self.timeout_id)
            self.timeout_id = None
        self.popup.hide()

    def show_popup(self):
        result_count = self.tree.get_model().iter_n_children(None)
        if result_count < 1:
            self.hide_popup()
            return

        if not self._parent_click_watcher:
            self._parent_click_watcher = self.get_toplevel().connect("button-press-event", self._on_focus_out_event)

        fact = Fact(self.filter)
        time = ''
        if fact.start_time:
            time = fact.start_time.strftime("%H:%M")
            if fact.end_time:
                time += "-%s" % fact.end_time.strftime("%H:%M")

        self.time_icon_column.set_visible(fact.start_time is not None and self.filter.find("@") == -1)
        self.time_column.set_visible(fact.start_time is not None and self.filter.find("@") == -1)


        self.activity_column.set_visible(self.filter.find("@") == -1)
        self.category_column.set_visible(self.filter.find("@") != -1)


        #set proper background color (we can do that only on a realised widget)
        bgcolor = self.get_style().bg[gtk.STATE_NORMAL]
        self.time_icon_cell.set_property("cell-background-gdk", bgcolor)
        self.time_cell.set_property("cell-background-gdk", bgcolor)

        text_color = self.get_style().text[gtk.STATE_NORMAL]
        category_color = graphics.Colors.contrast(text_color,  100)


        #move popup under the widget
        alloc = self.get_allocation()

        #TODO - this is clearly unreliable as we calculate tree row size based on our gtk entry
        popup_height = (alloc.height-6) * min([result_count, self.max_results])
        self.tree.parent.set_size_request(alloc.width, popup_height)
        self.popup.resize(alloc.width, popup_height)

        x, y = self.get_parent_window().get_origin()
        y = y + alloc.y

        if y + alloc.height + popup_height < self.get_screen().get_height():
            y = y + alloc.height
        else:
            y = y - popup_height

        self.popup.move(x + alloc.x, y)

        self.popup.show_all()

    def complete_inline(self):
        model = self.tree.get_model()
        subject = self.get_text()

        if not subject or model.iter_n_children(None) == 0:
            return

        prefix_length = 0

        labels = [row[0] for row in model]
        shortest = min([len(label) for label in labels])
        first = labels[0] #since we are looking for common prefix, we do not care which label we use for comparisons

        for i in range(len(subject), shortest):
            letter_matching = all([label[i]==first[i] for label in labels])

            if not letter_matching:
                break

            prefix_length +=1

        if prefix_length:
            prefix = first[len(subject):len(subject)+prefix_length]
            self.set_text("%s%s" % (self.filter, prefix))
            self.select_region(len(self.filter), len(self.filter) + prefix_length)

    def refresh_activities(self):
        # scratch category cache so it gets repopulated on demand
        self.categories = None

    def populate_suggestions(self):
        if self.get_selection_bounds():
            cursor = self.get_selection_bounds()[0]
        else:
            cursor = self.get_position()

        if self.activities and self.categories and self.filter == self.get_text().decode('utf8', 'replace')[:cursor]:
            return #same thing, no need to repopulate

        self.filter = self.get_text().decode('utf8', 'replace')#[:cursor]
        fact = Fact(self.filter)

        # do not cache as ordering and available options change over time
        self.activities = runtime.storage.get_activities(fact.activity)
        self.external_activities = self.external.get_activities(fact.activity)
        new_activities = []
        for activity in self.activities:
            match = re.match("^(#\d+: )", activity['name'])
            if match and self.external_activities:
                ticket_prefix = match.group(1)
                delete = False
                for external_activity in self.external_activities:
                    if external_activity['name'].startswith(ticket_prefix):
                        delete = True
                if not delete:
                    new_activities.append(activity)
            else:
                new_activities.append(activity)
                
        self.activities = new_activities
                    
        #self.activities.extend(self.external_activities)

        self.categories = self.categories or runtime.storage.get_categories()


        time = ''
        if fact.start_time:
            time = fact.start_time.strftime("%H:%M")
            if fact.end_time:
                time += "-%s" % fact.end_time.strftime("%H:%M")


        store = self.tree.get_model()
        if not store:
            store = gtk.ListStore(str, str, str, str, str, str)
            self.tree.set_model(store)
        store.clear()

        if self.filter.find("@") > 0:
            key = self.filter[self.filter.find("@")+1:].decode('utf8', 'replace').lower()
            for category in self.categories:
                if key in category['name'].decode('utf8', 'replace').lower():
                    fillable = (self.filter[:self.filter.find("@") + 1] + category['name'])
                    store.append([fillable, self.filter[:self.filter.find("@")], category['name'], time, category.get('rt_id'), None])
        else:
            key = fact.activity.decode('utf8', 'replace').lower()
            activities_to_append = []
            if conf.get("rt_activities_only"):
                if not self.external_activities:
                    for a in self.activities:
                        activities_to_append.append(a)
                else:
                    for a in self.external_activities:
                        activities_to_append.append(a)
            else:
                for a in self.activities:
                    activities_to_append.append(a)
                if self.external_activities:
                    for a in self.external_activities:
                        activities_to_append.append(a)

            filtered = []
            names = []
            for a in activities_to_append:
                if not a['name'] in names:
                    filtered.append(a)
                    names.append(a['name'])
            
            for activity in filtered:
                fillable = activity['name'].lower()
                minutes = None
                if activity['category']:
                    fillable += "@%s" % activity['category']

                if time: #as we also support deltas, for the time we will grab anything up to first space
                    minutes = self.filter.split(" ", 1)[0]
                    fillable = "%s %s" % (minutes, fillable)

                store.append([fillable, activity['name'].lower(), activity['category'], time, activity.get('rt_id'), minutes])

    def after_activity_update(self, widget):
        self.refresh_activities()

    def _on_focus_out_event(self, widget, event):
        self.hide_popup()

    def _on_text_changed(self, widget):
        self.news = True

    def _on_button_press_event(self, button, event):
        self._populate_and_show_delayed()
        
    def _populate_and_show_delayed(self):
        if self.timeout_id:
            gobject.source_remove(self.timeout_id)
            self.timeout_id = None
        self.timeout_id = gobject.timeout_add(750, self._populate_and_show)
        
    def _populate_and_show(self):
        self.populate_suggestions()
        self.show_popup()
        if self.timeout_id:
            gobject.source_remove(self.timeout_id)
            self.timeout_id = None

    def _on_key_release_event(self, entry, event):
        if (event.keyval in (gtk.keysyms.Return, gtk.keysyms.KP_Enter)):
            if self.popup.get_property("visible"):
                if self.tree.get_cursor()[0]:
                    selected = self._get_selected_text(self.tree)
#                    self.set_text(self.tree.get_model()[self.tree.get_cursor()[0][0]][0])
                    self.set_text(selected)
                self.hide_popup()
                self.set_position(len(self.get_text()))
            else:
                self._on_selected()

        elif (event.keyval == gtk.keysyms.Escape):
            if self.popup.get_property("visible"):
                self.hide_popup()
                return True
            else:
                return False
        elif event.keyval in (gtk.keysyms.Up, gtk.keysyms.Down):
            return False
        else:
            self._populate_and_show_delayed()

            #if event.keyval not in (gtk.keysyms.Delete, gtk.keysyms.BackSpace):
            #    self.complete_inline()




    def _on_key_press_event(self, entry, event):

        if event.keyval in (gtk.keysyms.Up, gtk.keysyms.Down):
            cursor = self.tree.get_cursor()

            if not cursor or not cursor[0]:
                self.tree.set_cursor(0)
                return True

            i = cursor[0][0]

            if event.keyval == gtk.keysyms.Up:
                i-=1
            elif event.keyval == gtk.keysyms.Down:
                i+=1

            # keep it in the sane borders
            i = min(max(i, 0), len(self.tree.get_model()) - 1)

            self.tree.set_cursor(i)
            self.tree.scroll_to_cell(i, use_align = True, row_align = 0.4)
            return True
        else:
            return False

    def _on_tree_button_press_event(self, tree, event):
        self.set_text(self._get_selected_text(tree))
        self.hide_popup()
        self.set_position(len(self.get_text()))
        
    def _get_selected_text(self, tree):
        model, iter = tree.get_selection().get_selected()
        #TODO tutaj jest błąd!
        name = model.get_value(iter, 1)
        rt_id = model.get_value(iter, 4)
        delta_time = model.get_value(iter, 5)
        if delta_time:
            name = ' '.join([delta_time, name])
        
        match = re.match(TICKET_NAME_REGEX, name)
        category = ""
        if not rt_id and match:
            rt_id = match.group(1)
        if rt_id:
            category = self.external.get_ticket_category(rt_id)
        if not category:
            category = model.get_value(iter, 2)
        return '@'.join([name, category])

    def _on_selected(self):
        if self.news and self.get_text().strip():
            self.set_position(len(self.get_text()))
            self.emit("value-entered")

        self.news = False
