#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2014 Toms Bauģis <toms.baugis at gmail.com>

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

import bisect
import datetime as dt
import itertools
import webbrowser

from collections import defaultdict

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import PangoCairo as pangocairo
from gi.repository import Pango as pango
import cairo

import hamster.client
from hamster.lib import graphics
from hamster import reports
from hamster.lib import stuff
from hamster import widgets
from hamster.lib.configuration import dialogs
from hamster.lib.pytweener import Easing

from widgets.dates import RangePick
from widgets.facttree import FactTree


class HeaderBar(gtk.HeaderBar):
    def __init__(self):
        gtk.HeaderBar.__init__(self)
        self.set_show_close_button(True)

        box = gtk.Box(False)
        time_back = gtk.Button.new_from_icon_name("go-previous-symbolic", gtk.IconSize.MENU)
        time_forth = gtk.Button.new_from_icon_name("go-next-symbolic", gtk.IconSize.MENU)

        box.add(time_back)
        box.add(time_forth)
        gtk.StyleContext.add_class(box.get_style_context(), "linked")
        self.pack_start(box)

        self.range_pick = RangePick(dt.datetime.today()) # TODO - use hamster day
        self.pack_start(self.range_pick)

        self.add_activity_button = gtk.Button()
        self.add_activity_button.set_image(gtk.Image.new_from_icon_name("list-add-symbolic",
                                                                        gtk.IconSize.MENU))
        self.pack_end(self.add_activity_button)

        self.search_button = gtk.ToggleButton()
        self.search_button.set_image(gtk.Image.new_from_icon_name("edit-find-symbolic",
                                                                  gtk.IconSize.MENU))
        self.pack_end(self.search_button)

        self.system_button = gtk.MenuButton()
        self.system_button.set_image(gtk.Image.new_from_icon_name("emblem-system-symbolic",
                                                                  gtk.IconSize.MENU))
        self.pack_end(self.system_button)

        self.system_menu = gtk.Menu()
        self.system_button.set_popup(self.system_menu)
        self.menu_export = gtk.MenuItem(label="Export...")
        self.system_menu.append(self.menu_export)
        self.menu_prefs = gtk.MenuItem(label="Tracking Settings")
        self.system_menu.append(self.menu_prefs)
        self.system_menu.show_all()


        time_back.connect("clicked", self.on_time_back_click)
        time_forth.connect("clicked", self.on_time_forth_click)
        self.connect("button-press-event", self.on_button_press)

    def on_button_press(self, bar, event):
        """swallow clicks on the interactive parts to avoid triggering
        switch to full-window"""
        return True

    def on_time_back_click(self, button):
        self.range_pick.prev_range()

    def on_time_forth_click(self, button):
        self.range_pick.next_range()


class StackedBar(graphics.Sprite):
    def __init__(self, width=0, height=0, vertical=None, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)

        #: orientation, horizontal by default
        self.vertical = vertical or False

        #: allocated width
        self.width = width

        #: allocated height
        self.height = height

        self._items = []
        self.connect("on-render", self.on_render)

        #: color scheme to use, graphics.colors.category10 by default
        self.colors = graphics.Colors.category10
        self.colors = ["#95CACF", "#A2CFB6", "#D1DEA1", "#E4C384", "#DE9F7B"]

        self._seen_keys = []


    def set_items(self, items):
        """expects a list of key, value to work with"""
        res = []
        max_value = sum((rec[1] for rec in items))
        for key, val in items:
            res.append((key, val, val * 1.0 / max_value))
        self._items = res


    def _take_color(self, key):
        if key in self._seen_keys:
            index = self._seen_keys.index(key)
        else:
            self._seen_keys.append(key)
            index = len(self._seen_keys) - 1
        return self.colors[index % (len(self.colors) + 1)]


    def on_render(self, sprite):
        if not self._items:
            self.graphics.clear()
            return

        max_width = self.width - 1 * len(self._items)
        for i, (key, val, normalized) in enumerate(self._items):
            color = self._take_color(key)

            width = int(normalized * max_width)
            self.graphics.rectangle(0, 0, width, self.height)
            self.graphics.fill(color)
            self.graphics.translate(width + 1, 0)



class Totals(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.set_size_request(200, 70)
        self.category_totals = graphics.Label(color=self._style.get_color(gtk.StateFlags.NORMAL),
                                              ellipsize=pango.EllipsizeMode.END)
        self.stacked_bar = StackedBar(height=25, y=25)
        self.add_child(self.category_totals, self.stacked_bar)

        self.totals = {}

        self.instructions_label = graphics.Label("Click to see stats",
                                                 color=self._style.get_color(gtk.StateFlags.NORMAL),
                                                 y=60,
                                                 alignment=pango.Alignment.CENTER)
        self.add_child(self.instructions_label)
        self.collapsed = True

        self.stub_label = graphics.Label(markup="<b>Here be stats,\ntune in laters!</b>",
                                         color="#bbb",
                                         size=60,
                                         y=90,
                                         alignment=pango.Alignment.CENTER)
        self.add_child(self.stub_label)

        # for use in animation
        self.height_proxy = graphics.Sprite(x=0)
        self.height_proxy.height = 70
        self.add_child(self.height_proxy)

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-click", self.on_click)
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)


    def set_facts(self, facts):
        totals = defaultdict(lambda: defaultdict(dt.timedelta))
        for fact in facts:
            totals['categories'][fact.category] += fact.delta

        for key, group in totals.iteritems():
            totals[key] = sorted(group.iteritems(), key=lambda x: x[1], reverse=True)
        self.totals = totals

        self.stacked_bar.set_items([(cat, delta.total_seconds() / 60.0) for cat, delta in totals['categories']])
        self.category_totals.markup = ", ".join("<b>%s:</b> %s" % (cat, stuff.format_duration(hours)) for cat, hours in totals['categories'])

    def on_click(self, scene, sprite, event):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.change_height(70)
            self.instructions_label.animate(opacity=1, easing=Easing.Expo.ease_in)
        else:
            self.change_height(300)
            self.instructions_label.animate(opacity=0, easing=Easing.Expo.ease_out)

    def on_mouse_enter(self, scene, event):
        if not self.collapsed:
            return
        self.change_height(100)

    def on_mouse_leave(self, scene, event):
        if not self.collapsed:
            return

        def delayed_leave(sprite):
            self.change_height(70)

        self.height_proxy.animate(x=50, delay=0.5, duration=0,
                                  on_complete=delayed_leave,
                                  on_update=lambda sprite: sprite.redraw())

    def change_height(self, new_height):
        self.stop_animation(self.height_proxy)
        def on_update_dummy(sprite):
            self.set_size_request(200, sprite.height)

        self.animate(self.height_proxy,
                     height=new_height,
                     on_update=on_update_dummy,
                     easing=Easing.Expo.ease_out)


    def on_enter_frame(self, scene, context):
        context.translate(10, 10)
        for sprite in self.sprites:
            if sprite == self.category_totals:
                sprite.max_width = self.width - 15
            sprite.width = self.width - 15


class Overview(gobject.GObject):
    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, parent = None):
        gobject.GObject.__init__(self)
        self.parent = parent

        self.window = gtk.Window()
        self.window.set_position(gtk.WindowPosition.CENTER)
        self.window.set_default_icon_name("hamster-time-tracker")
        self.window.set_default_size(700, 500)

        self.storage = hamster.client.Storage()
        self.storage.connect("facts-changed", self.on_facts_changed)
        self.storage.connect("activities-changed", self.on_facts_changed)

        self.header_bar = HeaderBar()
        self.window.set_titlebar(self.header_bar)

        main = gtk.Box(orientation=1)
        self.window.add(main)

        self.report_chooser = None


        self.search_box = gtk.Revealer()

        space = gtk.Box()
        space.set_border_width(5)
        self.search_box.add(space)
        self.filter_entry = gtk.Entry()
        self.filter_entry.set_icon_from_icon_name(gtk.EntryIconPosition.PRIMARY,
                                                  "edit-find-symbolic")
        self.filter_entry.connect("changed", self.on_search_changed)
        self.filter_entry.connect("icon-press", self.on_search_icon_press)

        space.pack_start(self.filter_entry, True, True, 0)
        main.pack_start(self.search_box, False, True, 0)


        window = gtk.ScrolledWindow()
        window.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        self.fact_tree = FactTree()
        self.fact_tree.connect("on-activate-row", self.on_row_activated)

        window.add(self.fact_tree)
        main.pack_start(window, True, True, 1)

        self.totals = Totals()
        main.pack_start(self.totals, False, True, 1)

        date_range = stuff.week(dt.datetime.today()) # TODO - do the hamster day
        self.header_bar.range_pick.set_range(*date_range)
        self.header_bar.range_pick.connect("range-selected", self.on_range_selected)
        self.header_bar.add_activity_button.connect("clicked", self.on_add_activity_clicked)
        self.header_bar.search_button.connect("toggled", self.on_search_toggled)

        self.header_bar.menu_prefs.connect("activate", self.on_prefs_clicked)
        self.header_bar.menu_export.connect("activate", self.on_export_clicked)


        self.window.connect("key-press-event", self.on_key_press)
        self.window.connect("delete-event", self.on_close)

        self.facts = []
        self.find_facts()
        self.window.show_all()

    def on_key_press(self, window, event):
        if self.filter_entry.has_focus():
            if event.keyval == gdk.KEY_Escape:
                self.header_bar.search_button.set_active(False)
                return True
            elif event.keyval in (gdk.KEY_Up, gdk.KEY_Down,
                                  gdk.KEY_Page_Up, gdk.KEY_Page_Down,
                                  gdk.KEY_Return):
                self.fact_tree.on_key_press(self, event)
                return True

        if self.fact_tree.has_focus() or self.totals.has_focus():
            if event.keyval == gdk.KEY_Tab:
                pass # TODO - deal with tab as our scenes eat up navigation

        if event.state & gdk.ModifierType.CONTROL_MASK:
            # the ctrl+things
            if event.keyval == gdk.KEY_f:
                self.header_bar.search_button.set_active(True)


    def find_facts(self):
        start, end = self.header_bar.range_pick.get_range()
        search_active = self.header_bar.search_button.get_active()
        search = "" if not search_active else self.filter_entry.get_text()
        search = "%s*" % search if search else "" # search anywhere

        self.facts = self.storage.get_facts(start, end, search_terms=search)
        self.fact_tree.set_facts(self.facts)
        self.totals.set_facts(self.facts)

    def on_range_selected(self, button, range_type, start, end):
        self.find_facts()

    def on_search_changed(self, entry):
        if entry.get_text():
            self.filter_entry.set_icon_from_icon_name(gtk.EntryIconPosition.SECONDARY,
                                                      "edit-clear-symbolic")
        else:
            self.filter_entry.set_icon_from_icon_name(gtk.EntryIconPosition.SECONDARY,
                                                      None)
        self.find_facts()

    def on_search_icon_press(self, entry, position, event):
        if position == gtk.EntryIconPosition.SECONDARY:
            self.filter_entry.set_text("")

    def on_facts_changed(self, event):
        self.find_facts()

    def on_add_activity_clicked(self, button):
        dialogs.edit.show(self)

    def on_row_activated(self, tree, day, fact):
        dialogs.edit.show(self, fact_id=fact.id)

    def on_search_toggled(self, button):
        active = button.get_active()
        self.search_box.set_reveal_child(active)
        #self.search_box.set_visible(active)
        if active:
            self.filter_entry.grab_focus()

    def on_prefs_clicked(self, menu):
        dialogs.prefs.show(self)

    def on_export_clicked(self, menu):
        start, end = self.header_bar.range_pick.get_range()

        def on_report_chosen(widget, format, path):
            self.report_chooser = None
            reports.simple(self.facts, start, end, format, path)

            if format == ("html"):
                webbrowser.open_new("file://%s" % path)
            else:
                try:
                    gtk.show_uri(gdk.Screen(), "file://%s" % os.path.split(path)[0], 0L)
                except:
                    pass # bug 626656 - no use in capturing this one i think

        def on_report_chooser_closed(widget):
            self.report_chooser = None

        if not self.report_chooser:
            self.report_chooser = widgets.ReportChooserDialog()
            self.report_chooser.connect("report-chosen", on_report_chosen)
            self.report_chooser.connect("report-chooser-closed",
                                        on_report_chooser_closed)
            self.report_chooser.show(start, end)
        else:
            self.report_chooser.present()


    def show(self):
        self.window.show()

    def on_close(self, widget, event):
        self.close_window()

    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            """
            for obj, handler in self.external_listeners:
                obj.disconnect(handler)
            """
            self.window.destroy()
            self.window = None
            self.emit("on-close")


if __name__ == '__main__':
    hamster = Overview()

    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()
