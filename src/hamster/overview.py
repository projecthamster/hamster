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

import logging

logger = logging.getLogger(__name__)  # noqa: E402

import sys
import threading
import webbrowser
from collections import defaultdict
from math import ceil

import cairo
from gi.repository import GLib as glib
from gi.repository import GObject as gobject
from gi.repository import Gdk as gdk
from gi.repository import Gtk as gtk
from gi.repository import Pango as pango
from gi.repository import PangoCairo as pangocairo

import hamster.client
from hamster import reports
from hamster import widgets
from hamster.lib import datetime as dt
from hamster.lib import graphics
from hamster.lib import layout
from hamster.lib import stuff
from hamster.lib.configuration import Controller, runtime
from hamster.lib.pytweener import Easing
from hamster.widgets.dates import RangePick
from hamster.widgets.facttree import FactTree


class HeaderBar(gtk.HeaderBar):
    def __init__(self):
        gtk.HeaderBar.__init__(self)
        self.set_show_close_button(True)

        box = gtk.Box(False)
        self.time_back = gtk.Button.new_from_icon_name("go-previous-symbolic", gtk.IconSize.MENU)
        self.time_forth = gtk.Button.new_from_icon_name("go-next-symbolic", gtk.IconSize.MENU)

        box.add(self.time_back)
        box.add(self.time_forth)
        gtk.StyleContext.add_class(box.get_style_context(), "linked")
        self.pack_start(box)

        self.range_pick = RangePick(dt.hday.today())
        self.pack_start(self.range_pick)

        self.system_button = gtk.MenuButton()
        self.system_button.set_image(gtk.Image.new_from_icon_name(
            "open-menu-symbolic", gtk.IconSize.MENU))
        self.system_button.set_tooltip_markup(_("Menu"))
        self.pack_end(self.system_button)

        self.search_button = gtk.ToggleButton()
        self.search_button.set_image(gtk.Image.new_from_icon_name(
            "edit-find-symbolic", gtk.IconSize.MENU))
        self.search_button.set_tooltip_markup(_("Filter activities"))
        self.pack_end(self.search_button)

        self.stop_button = gtk.Button()
        self.stop_button.set_image(gtk.Image.new_from_icon_name(
            "process-stop-symbolic", gtk.IconSize.MENU))
        self.stop_button.set_tooltip_markup(_("Stop tracking (Ctrl-SPACE)"))
        self.pack_end(self.stop_button)

        self.add_activity_button = gtk.Button()
        self.add_activity_button.set_image(gtk.Image.new_from_icon_name(
            "list-add-symbolic", gtk.IconSize.MENU))
        self.add_activity_button.set_tooltip_markup(_("Add activity (Ctrl-+)"))
        self.pack_end(self.add_activity_button)

        self.system_menu = gtk.Menu()
        self.system_button.set_popup(self.system_menu)
        self.menu_export = gtk.MenuItem(label=_("Export to file..."))
        self.system_menu.append(self.menu_export)
        self.menu_prefs = gtk.MenuItem(label=_("Tracking Settings"))
        self.system_menu.append(self.menu_prefs)
        self.menu_help = gtk.MenuItem(label=_("Help"))
        self.system_menu.append(self.menu_help)
        self.system_menu.show_all()

        self.time_back.connect("clicked", self.on_time_back_click)
        self.time_forth.connect("clicked", self.on_time_forth_click)
        self.connect("button-press-event", self.on_button_press)

    def on_button_press(self, bar, event):
        """swallow clicks on the interactive parts to avoid triggering
        switch to full-window"""
        return True

    def on_time_back_click(self, button):
        self.range_pick.prev_range()

    def on_time_forth_click(self, button):
        self.range_pick.next_range()


class StackedBar(layout.Widget):
    def __init__(self, width=0, height=0, vertical=None, **kwargs):
        layout.Widget.__init__(self, **kwargs)

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
        max_value = max(sum((rec[1] for rec in items)), 1)
        for key, val in items:
            res.append((key, val, val * 1.0 / max_value))
        self._items = res

    def _take_color(self, key):
        if key in self._seen_keys:
            index = self._seen_keys.index(key)
        else:
            self._seen_keys.append(key)
            index = len(self._seen_keys) - 1
        return self.colors[index % len(self.colors)]

    def on_render(self, sprite):
        if not self._items:
            self.graphics.clear()
            return

        max_width = self.alloc_w - 1 * len(self._items)
        for i, (key, val, normalized) in enumerate(self._items):
            color = self._take_color(key)

            width = int(normalized * max_width)
            self.graphics.rectangle(0, 0, width, self.height)
            self.graphics.fill(color)
            self.graphics.translate(width + 1, 0)


class Label(object):
    """a much cheaper label that would be suitable for cellrenderer"""

    def __init__(self, x=0, y=0, color=None, use_markup=False):
        self.x = x
        self.y = y
        self.color = color
        self.use_markup = use_markup

    def _set_text(self, text):
        if self.use_markup:
            self.layout.set_markup(text)
        else:
            self.layout.set_text(text, -1)

    def _show(self, g):
        if self.color:
            g.set_color(self.color)
        pangocairo.show_layout(g.context, self.layout)

    def show(self, g, text, x=0, y=0):
        g.save_context()
        g.move_to(x or self.x, y or self.y)
        self._set_text(text)
        self._show(g)
        g.restore_context()


class HorizontalBarChart(graphics.Sprite):
    def __init__(self, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.x_align = 0
        self.y_align = 0
        self.values = []

        self._label_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
        self.layout = pangocairo.create_layout(self._label_context)
        self.layout.set_font_description(pango.FontDescription(graphics._font_desc))
        self.layout.set_markup("Hamster")  # dummy
        # ellipsize the middle because depending on the use case,
        # the distinctive information can be either at the beginning or the end.
        self.layout.set_ellipsize(pango.EllipsizeMode.MIDDLE)
        self.layout.set_justify(True)
        self.layout.set_alignment(pango.Alignment.RIGHT)
        self.label_height = self.layout.get_pixel_size()[1]
        # should be updated by the parent
        self.label_color = gdk.RGBA()
        self.bar_color = gdk.RGBA()

        self._max = dt.timedelta(0)

    def set_values(self, values):
        """expects a list of 2-tuples"""
        self.values = values
        self.height = len(self.values) * 14
        self._max = max(rec[1] for rec in values) if values else dt.timedelta(0)

    def _draw(self, context, opacity, matrix):
        g = graphics.Graphics(context)
        g.save_context()
        g.translate(self.x, self.y)
        # arbitrary 3/4 total width for label, 1/4 for histogram
        hist_width = self.alloc_w // 4;
        margin = 10  # pixels
        label_width = self.alloc_w - hist_width - margin
        self.layout.set_width(label_width * pango.SCALE)
        label_h = self.label_height
        bar_start_x = label_width + margin
        for i, (label, value) in enumerate(self.values):
            g.set_color(self.label_color)
            duration_str = value.format(fmt="HH:MM")
            markup_label = stuff.escape_pango(str(label))
            markup_duration = stuff.escape_pango(duration_str)
            self.layout.set_markup("{}, <i>{}</i>".format(markup_label, markup_duration))
            y = int(i * label_h * 1.5)
            g.move_to(0, y)
            pangocairo.show_layout(context, self.layout)
            if self._max > dt.timedelta(0):
                w = ceil(hist_width * value.total_seconds() /
                         self._max.total_seconds())
            else:
                w = 1
            g.rectangle(bar_start_x, y, int(w), int(label_h))
            g.fill(self.bar_color)

        g.restore_context()


class Exporter(gtk.Box):
    def __init__(self, storage: hamster.client.Storage):
        gtk.Box.__init__(self, orientation=gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_border_width(12)

        self.progressbar = gtk.ProgressBar()
        self.progressbar.set_show_text(True)
        self.pack_start(self.progressbar, True, True, 0)

        self.start_button = gtk.Button.new_with_label(_("📤 Start export"))
        self.start_button.connect("clicked", self.on_start_button_clicked)
        self.pack_start(self.start_button, False, False, 1)

        self.connect("destroy", self.on_destroy_event)

        self.storage = storage
        self.export_thread = None
        self.facts = []

    def _init_labels(self):
        if not self.export_thread:
            self.progressbar.set_text(_("Waiting for action (%s activities to export)") % len(self.facts))
            self.progressbar.set_fraction(0)
            self.start_button.set_label(_("📤 Start export"))
            self.start_button.set_sensitive(True)

    def set_facts(self, facts):
        self.facts = list(filter(lambda f: not f.exported, facts))
        self._init_labels()

    def on_start_button_clicked(self, button):
        if not self.export_thread:
            self.export_thread = ExportThread(self.facts, self._update_progressbar, self._finish_export, self.storage)
            self.start_button.set_sensitive(False)
            self.start_button.set_label(_("Exporting..."))
            # start the thread
            self.export_thread.start()

    def _finish_export(self, interrupted):
        if interrupted:
            self.progressbar.set_text(_("Interrupted"))
        else:
            self.progressbar.set_fraction(1.0)
            self.progressbar.set_text(_("Done"))
        self.start_button.set_label(_("Done"))
        self.start_button.set_sensitive(False)
        self.export_thread = None

    def _update_progressbar(self, fraction, label):
        self.progressbar.set_fraction(fraction)
        self.progressbar.set_text(label)
        # self.done_button.set_label(_("Stop"))

    def on_destroy_event(self, event):
        if self.export_thread:
            self.export_thread.shutdown()

class ExportThread(threading.Thread):
    def __init__(self, facts, callback, finish_callback, storage: hamster.client.Storage):
        threading.Thread.__init__(self)
        self.storage = storage
        self.facts = facts
        self.callback = callback
        self.finish_callback = finish_callback
        self.steps = (len(self.facts) + 1)
        self.interrupt = False

    def run(self):
        glib.idle_add(self.callback, 0.0, _("Connecting to external source..."))
        for idx, fact in enumerate(self.facts):
            if self.interrupt:
                logger.info("Interrupting export thread")
                break
            fraction = float(idx + 1) / self.steps
            label = _("Exporting: %s - %s") % (fact.activity, fact.delta)
            glib.idle_add(self.callback, fraction, label)
            exported = self.storage.export_fact(fact.id)
            if exported:
                fact.exported = True
                self.storage.update_fact(fact.id, fact, False)
                pass
            else:
                logger.info("Fact not exported: %s" % fact.activity)

        glib.idle_add(self.finish_callback, self.interrupt)

    def shutdown(self):
        logger.info("Trying to shutdown")
        self.interrupt = True


class Totals(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.set_size_request(200, 70)
        self.category_totals = layout.Label(overflow=pango.EllipsizeMode.END,
                                            x_align=0,
                                            expand=False)
        self.stacked_bar = StackedBar(height=25, x_align=0, expand=False)

        box = layout.VBox(padding=10, spacing=5)
        self.add_child(box)

        box.add_child(self.category_totals, self.stacked_bar)

        self.totals = {}
        self.mouse_cursor = gdk.CursorType.HAND2

        self.instructions_label = layout.Label(_("Click to see stats"),
                                               color=self._style.get_color(gtk.StateFlags.NORMAL),
                                               padding=10,
                                               expand=False)

        box.add_child(self.instructions_label)
        self.collapsed = True

        main = layout.HBox(padding_top=10)
        box.add_child(main)

        self.stub_label = layout.Label(markup="<b>Here be stats,\ntune in laters!</b>",
                                       color="#bbb",
                                       size=60)

        self.activities_chart = HorizontalBarChart()
        self.categories_chart = HorizontalBarChart()
        self.tag_chart = HorizontalBarChart()

        main.add_child(self.activities_chart, self.categories_chart, self.tag_chart)

        # for use in animation
        self.height_proxy = graphics.Sprite(x=0)
        self.height_proxy.height = 70
        self.add_child(self.height_proxy)

        self.connect("on-click", self.on_click)
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)
        self.connect("state-flags-changed", self.on_state_flags_changed)
        self.connect("style-updated", self.on_style_changed)

    def set_facts(self, facts):
        totals = defaultdict(lambda: defaultdict(dt.timedelta))
        for fact in facts:
            for key in ('category', 'activity'):
                totals[key][getattr(fact, key)] += fact.delta

            for tag in fact.tags:
                totals["tag"][tag] += fact.delta

        for key, group in totals.items():
            totals[key] = sorted(group.items(), key=lambda x: x[1], reverse=True)
        self.totals = totals

        self.activities_chart.set_values(totals['activity'])
        self.categories_chart.set_values(totals['category'])
        self.tag_chart.set_values(totals['tag'])

        self.stacked_bar.set_items([(cat, delta.total_seconds() / 60.0) for cat, delta in totals['category']])

        grand_total = sum(delta.total_seconds() / 60
                          for __, delta in totals['activity'])
        self.category_totals.markup = "<b>Total: </b>%s; " % stuff.format_duration(grand_total)
        self.category_totals.markup += ", ".join(
            "<b>%s:</b> %s" % (stuff.escape_pango(cat), stuff.format_duration(hours)) for cat, hours in
            totals['category'])

    def on_click(self, scene, sprite, event):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.change_height(70)
            self.instructions_label.visible = True
            self.instructions_label.opacity = 0
            self.instructions_label.animate(opacity=1, easing=Easing.Expo.ease_in)
        else:
            self.change_height(300)
            self.instructions_label.visible = False

        self.mouse_cursor = gdk.CursorType.HAND2 if self.collapsed else None

    def on_mouse_enter(self, scene, event):
        if not self.collapsed:
            return

        def delayed_leave(sprite):
            self.change_height(100)

        self.height_proxy.animate(x=50, delay=0.5, duration=0,
                                  on_complete=delayed_leave,
                                  on_update=lambda sprite: sprite.redraw())

    def on_mouse_leave(self, scene, event):
        if not self.collapsed:
            return

        def delayed_leave(sprite):
            self.change_height(70)

        self.height_proxy.animate(x=50, delay=0.5, duration=0,
                                  on_complete=delayed_leave,
                                  on_update=lambda sprite: sprite.redraw())

    def on_state_flags_changed(self, previous_state, _):
        self.update_colors()

    def on_style_changed(self, _):
        self.update_colors()

    def change_height(self, new_height):
        self.stop_animation(self.height_proxy)

        def on_update_dummy(sprite):
            self.set_size_request(200, sprite.height)

        self.animate(self.height_proxy,
                     height=new_height,
                     on_update=on_update_dummy,
                     easing=Easing.Expo.ease_out)

    def update_colors(self):
        color = self._style.get_color(self.get_state())
        self.instructions_label.color = color
        self.category_totals.color = color
        self.activities_chart.label_color = color
        self.categories_chart.label_color = color
        self.tag_chart.label_color = color
        bg_color = self._style.get_background_color(self.get_state())
        bar_color = self.colors.mix(bg_color, color, 0.6)
        self.activities_chart.bar_color = bar_color
        self.categories_chart.bar_color = bar_color
        self.tag_chart.bar_color = bar_color


class Overview(Controller):
    def __init__(self):
        Controller.__init__(self)

        self.prefs_dialog = None  # preferences dialog controller

        self.window.set_position(gtk.WindowPosition.CENTER)
        self.window.set_default_icon_name("org.gnome.Hamster.GUI")
        self.window.set_default_size(1000, 700)

        self.storage = hamster.client.Storage()
        self.storage.connect("facts-changed", self.on_facts_changed)
        self.storage.connect("activities-changed", self.on_facts_changed)

        self.header_bar = HeaderBar()
        self.window.set_titlebar(self.header_bar)

        main = gtk.Box(orientation=1)
        self.window.add(main)

        self.report_chooser = None

        self.search_box = gtk.Revealer()

        space = gtk.Box(border_width=5)
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
        self.fact_tree.connect("on-delete-called", self.on_row_delete_called)
        self.fact_tree.connect("on-toggle-exported-row", self.on_row_toggle_exported_called)

        window.add(self.fact_tree)
        main.pack_start(window, True, True, 1)

        self.exporter = Exporter(self.storage)
        main.pack_start(self.exporter, False, True, 1)

        self.totals = Totals()
        main.pack_start(self.totals, False, True, 1)

        # FIXME: should store and recall date_range from hamster.lib.configuration.conf
        hamster_day = dt.hday.today()
        self.header_bar.range_pick.set_range(hamster_day)
        self.header_bar.range_pick.connect("range-selected", self.on_range_selected)
        self.header_bar.add_activity_button.connect("clicked", self.on_add_activity_clicked)
        self.header_bar.stop_button.connect("clicked", self.on_stop_clicked)
        self.header_bar.search_button.connect("toggled", self.on_search_toggled)

        self.header_bar.menu_prefs.connect("activate", self.on_prefs_clicked)
        self.header_bar.menu_export.connect("activate", self.on_export_clicked)
        self.header_bar.menu_help.connect("activate", self.on_help_clicked)

        self.window.connect("key-press-event", self.on_key_press)

        self.facts = []
        self.find_facts()

        # update every minute (necessary if an activity is running)
        gobject.timeout_add_seconds(60, self.on_timeout)
        self.window.show_all()

    def on_key_press(self, window, event):
        if self.filter_entry.has_focus():
            if event.keyval == gdk.KEY_Escape:
                self.filter_entry.set_text("")
                self.header_bar.search_button.set_active(False)
                return True
        elif event.keyval in (gdk.KEY_Up, gdk.KEY_Down,
                              gdk.KEY_Home, gdk.KEY_End,
                              gdk.KEY_Page_Up, gdk.KEY_Page_Down,
                              gdk.KEY_Return, gdk.KEY_Delete):
            # These keys should work even when fact_tree does not have focus
            self.fact_tree.on_key_press(self, event)
            return True  # stop event propagation
        elif event.keyval == gdk.KEY_Left:
            self.header_bar.time_back.emit("clicked")
            return True
        elif event.keyval == gdk.KEY_Right:
            self.header_bar.time_forth.emit("clicked")
            return True

        if self.fact_tree.has_focus() or self.totals.has_focus():
            if event.keyval == gdk.KEY_Tab:
                pass  # TODO - deal with tab as our scenes eat up navigation

        if event.state & gdk.ModifierType.CONTROL_MASK:
            # the ctrl+things
            if event.keyval == gdk.KEY_f:
                self.header_bar.search_button.set_active(True)
            elif event.keyval == gdk.KEY_n:
                self.start_new_fact(clone_selected=False)
            elif event.keyval == gdk.KEY_r:
                # Resume/run; clear separation between Ctrl-R and Ctrl-N
                self.start_new_fact(clone_selected=True, fallback=False)
            elif event.keyval == gdk.KEY_space:
                self.storage.stop_tracking()
            elif event.keyval in (gdk.KEY_KP_Add, gdk.KEY_plus, gdk.KEY_equal):
                # same as pressing the + icon
                self.start_new_fact(clone_selected=True, fallback=True)

        if event.keyval == gdk.KEY_Escape:
            self.close_window()

    def find_facts(self):
        start, end = self.header_bar.range_pick.get_range()
        search_active = self.header_bar.search_button.get_active()
        search = "" if not search_active else self.filter_entry.get_text()
        search = "%s*" % search if search else ""  # search anywhere
        self.facts = self.storage.get_facts(start, end, search_terms=search)
        self.fact_tree.set_facts(self.facts)
        self.totals.set_facts(self.facts)
        self.exporter.set_facts(self.facts)
        self.header_bar.stop_button.set_sensitive(
            self.facts and not self.facts[-1].end_time)

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
        self.start_new_fact(clone_selected=True, fallback=True)

    def on_stop_clicked(self, button):
        self.storage.stop_tracking()

    def on_row_activated(self, tree, day, fact):
        self.present_fact_controller("edit", fact_id=fact.id)

    def on_row_delete_called(self, tree, fact):
        self.storage.remove_fact(fact.id)
        self.find_facts()

    def on_row_toggle_exported_called(self, tree, fact):
        fact.exported = not fact.exported
        self.storage.update_fact(fact.id, fact)

    def on_search_toggled(self, button):
        active = button.get_active()
        self.search_box.set_reveal_child(active)
        if active:
            self.filter_entry.grab_focus()

    def on_timeout(self):
        # TODO: should update only the running FactTree row (if any), and totals
        self.find_facts()
        # The timeout will stop if returning False
        return True

    def on_help_clicked(self, menu):
        uri = "help:hamster"
        try:
            gtk.show_uri(None, uri, gdk.CURRENT_TIME)
        except glib.Error:
            msg = sys.exc_info()[1].args[0]
            dialog = gtk.MessageDialog(self.window, 0, gtk.MessageType.ERROR,
                                       gtk.ButtonsType.CLOSE,
                                       _("Failed to open {}").format(uri))
            fmt = _('Error: "{}" - is a help browser installed on this computer?')
            dialog.format_secondary_text(fmt.format(msg))
            dialog.run()
            dialog.destroy()

    def on_prefs_clicked(self, menu):
        app = self.window.get_property("application")
        app.activate_action("preferences")

    def on_export_clicked(self, menu):
        if self.report_chooser:
            self.report_chooser.present()
            return

        start, end = self.header_bar.range_pick.get_range()

        def on_report_chosen(widget, format, path):
            self.report_chooser = None
            reports.simple(self.facts, start, end, format, path)

            if format == ("html"):
                webbrowser.open_new("file://%s" % path)
            else:
                try:
                    gtk.show_uri(None, "file://%s" % path, gdk.CURRENT_TIME)
                except:
                    pass  # bug 626656 - no use in capturing this one i think

        def on_report_chooser_closed(widget):
            self.report_chooser = None

        self.report_chooser = widgets.ReportChooserDialog()
        self.report_chooser.connect("report-chosen", on_report_chosen)
        self.report_chooser.connect("report-chooser-closed", on_report_chooser_closed)
        self.report_chooser.show(start, end)

    def present_fact_controller(self, action, fact_id=0):
        app = self.window.get_property("application")
        app.present_fact_controller(action, fact_id=fact_id)

    def start_new_fact(self, clone_selected=True, fallback=True):
        """Start now a new fact.
        clone_selected (bool): whether to start a clone of currently
            selected fact or to create a new fact from scratch.
        fallback (bool): if True, fall back to creating from scratch
                         in case of no selected fact.
        """
        if not clone_selected:
            self.present_fact_controller("add")
        elif self.fact_tree.current_fact:
            self.present_fact_controller("clone",
                                         fact_id=self.fact_tree.current_fact.id)
        elif fallback:
            self.present_fact_controller("add")

    def close_window(self):
        self.window.destroy()
        self.window = None
        self._gui = None
        self.emit("on-close")
