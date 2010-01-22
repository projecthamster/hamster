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


import pygtk
pygtk.require('2.0')

import os
import datetime as dt
import calendar
import webbrowser

import gtk, gobject
import pango

import stuff
from hamster.i18n import C_
from configuration import runtime, conf, dialogs
import widgets, reports

from overview_activities import OverviewBox
from overview_totals import TotalsBox


class Overview(object):
    def __init__(self, parent = None):
        self.parent = parent# determine if app should shut down on close
        self._gui = stuff.load_ui_file("overview.ui")
        self.report_chooser = None

        self.facts = None

        self.window = self.get_widget("tabs_window")

        self.day_start = conf.get("day_start_minutes")
        self.day_start = dt.time(self.day_start / 60, self.day_start % 60)

        self.view_date = (dt.datetime.today() - dt.timedelta(hours = self.day_start.hour,
                                                        minutes = self.day_start.minute)).date()

        #set to monday
        self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)

        # look if we need to start on sunday or monday
        self.start_date = self.start_date + dt.timedelta(stuff.locale_first_weekday())

        # see if we have not gotten carried away too much in all these calculations
        if (self.view_date - self.start_date) == dt.timedelta(7):
            self.start_date += dt.timedelta(7)

        self.end_date = self.start_date + dt.timedelta(6)


        self.overview = OverviewBox()
        self.get_widget("overview_tab").add(self.overview)
        self.fact_tree = self.overview.fact_tree # TODO - this is upside down, should maybe get the overview tab over here
        self.fact_tree.connect("cursor-changed", self.on_fact_selection_changed)

        self.reports = TotalsBox()
        self.get_widget("reports_tab").add(self.reports)

        self.range_combo = gtk.combo_box_new_text()
        self.range_combo.append_text(_("Week"))
        self.range_combo.append_text(_("Month"))
        self.range_combo.append_text(_("Date Range"))
        self.range_combo.set_active(0)
        self.range_combo.connect("changed", self.on_range_combo_changed)



        self.get_widget("range_pick").add(self.range_combo)


        self.start_date_input = widgets.DateInput(self.start_date)
        self.start_date_input.connect("date-entered", self.on_start_date_entered)
        self.get_widget("range_start_box").add(self.start_date_input)

        self.end_date_input = widgets.DateInput(self.end_date)
        self.end_date_input.connect("date-entered", self.on_end_date_entered)
        self.get_widget("range_end_box").add(self.end_date_input)

        self.timechart = widgets.TimeChart()
        self.timechart.day_start = self.day_start

        self.get_widget("by_day_box").add(self.timechart)

        self._gui.connect_signals(self)
        runtime.dispatcher.add_handler('activity_updated', self.after_activity_update)
        runtime.dispatcher.add_handler('day_updated', self.after_activity_update)
        runtime.dispatcher.add_handler('conf_changed', self.on_conf_change)

        if conf.get("overview_window_maximized"):
            self.window.maximize()
        else:
            window_box = conf.get("overview_window_box")
            if window_box:
                x,y,w,h = (int(i) for i in window_box)
                self.window.move(x, y)
                self.window.move(x, y)
                self.window.resize(w, h)
            else:
                self.window.set_position(gtk.WIN_POS_CENTER)

        self.window.show_all()
        self.search()


    def search(self):
        if self.start_date > self.end_date: # make sure the end is always after beginning
            self.start_date, self.end_date = self.end_date, self.start_date

        self.start_date_input.set_date(self.start_date)
        self.end_date_input.set_date(self.end_date)

        search_terms = self.get_widget("search").get_text().decode("utf8", "replace")
        self.facts = runtime.storage.get_facts(self.start_date, self.end_date, search_terms)

        self.get_widget("report_button").set_sensitive(len(self.facts) > 0)

        self.set_title()

        durations = [(fact["start_time"], fact["delta"]) for fact in self.facts]
        self.timechart.draw(durations, self.start_date, self.end_date)


        if self.get_widget("window_tabs").get_current_page() == 0:
            self.overview.search(self.start_date, self.end_date, self.facts)
            self.reports.search(self.start_date, self.end_date, self.facts)
        else:
            self.reports.search(self.start_date, self.end_date, self.facts)
            self.overview.search(self.start_date, self.end_date, self.facts)

    def set_title(self):
        start_date, end_date = self.start_date, self.end_date
        dates_dict = stuff.dateDict(start_date, "start_")
        dates_dict.update(stuff.dateDict(end_date, "end_"))

        if start_date == end_date:
            # date format for overview label when only single day is visible
            # Using python datetime formatting syntax. See:
            # http://docs.python.org/library/time.html#time.strftime
            start_date_str = start_date.strftime(_("%B %d, %Y"))
            # Overview label if looking on single day
            self.title = start_date_str
        elif start_date.year != end_date.year:
            # overview label if start and end years don't match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            self.title = _(u"%(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif start_date.month != end_date.month:
            # overview label if start and end month do not match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            self.title = _(u"%(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        else:
            # overview label for interval in same month
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            self.title = _(u"%(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict

        self.get_widget("range_title").set_text(self.title)


    def on_conf_change(self, event, data):
        key, value = data
        if key == "day_start_minutes":
            self.day_start = dt.time(value / 60, value % 60)
            self.timechart.day_start = self.day_start
            self.search()

    def on_fact_selection_changed(self, tree):
        """ enables and disables action buttons depending on selected item """
        fact = tree.get_selected_fact()
        real_fact = fact is not None and isinstance(fact, dict)

        self.get_widget('remove').set_sensitive(real_fact)
        self.get_widget('edit').set_sensitive(real_fact)

        return True

    def after_activity_update(self, widget, renames):
        self.search()

    def on_search_activate(self, widget):
        self.search()

    def on_report_button_clicked(self, widget):
        def on_report_chosen(widget, format, path):
            self.report_chooser = None
            reports.simple(self.facts, self.start_date, self.end_date, format, path)

            if format == ("html"):
                webbrowser.open_new("file://%s" % path)
            else:
                gtk.show_uri(gtk.gdk.Screen(),
                             "file://%s" % os.path.split(path)[0], 0L)

        def on_report_chooser_closed(widget):
            self.report_chooser = None

        if not self.report_chooser:
            self.report_chooser = widgets.ReportChooserDialog()
            self.report_chooser.connect("report-chosen", on_report_chosen)
            self.report_chooser.connect("report-chooser-closed",
                                        on_report_chooser_closed)
            self.report_chooser.show(self.start_date, self.end_date)
        else:
            self.report_chooser.present()



    def on_range_combo_changed(self, combo):
        idx = combo.get_active()

        self.get_widget("preset_range").hide()
        self.get_widget("range_box").hide()

        if idx == 2: # date range
            self.get_widget("range_box").show()
        else:
            if idx == 0: # week
                self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
                self.start_date = self.start_date + dt.timedelta(stuff.locale_first_weekday())
                self.end_date = self.start_date + dt.timedelta(6)
                self.get_widget("preset_range").show()

            elif idx == 1: #month
                self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
                first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
                self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
                self.get_widget("preset_range").show()


            self.search()

    def on_tabs_window_configure_event(self, window, event):
        # this is required so that the rows would grow on resize
        self.fact_tree.fix_row_heights()


    def on_start_date_entered(self, input):
        self.start_date = input.get_date().date()
        self.view_date = self.start_date
        self.search()

    def on_end_date_entered(self, input):
        self.end_date = input.get_date().date()
        self.search()

    def _chosen_range(self):
        return self.range_combo.get_active()

    def on_prev_clicked(self, button):
        if self._chosen_range() == 0:  # week
            self.start_date -= dt.timedelta(7)
            self.end_date -= dt.timedelta(7)
        elif self._chosen_range() == 1: # month
            self.end_date = self.start_date - dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.end_date.year, self.end_date.month)
            self.start_date = self.end_date - dt.timedelta(days_in_month - 1)

        self.view_date = self.start_date
        self.search()

    def on_next_clicked(self, button):
        if self._chosen_range() == 0:  # week
            self.start_date += dt.timedelta(7)
            self.end_date += dt.timedelta(7)
        elif self._chosen_range() == 1: # month
            self.start_date = self.end_date + dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.start_date.year, self.start_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)

        self.view_date = self.start_date
        self.search()


    def on_home_clicked(self, button):
        self.view_date = (dt.datetime.today() - dt.timedelta(hours = self.day_start.hour,
                                                        minutes = self.day_start.minute)).date()
        if self._chosen_range() == 0: # week
            self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
            self.start_date = self.start_date + dt.timedelta(stuff.locale_first_weekday())
            self.end_date = self.start_date + dt.timedelta(6)

        elif self._chosen_range() == 1: # month
            self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
            first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)

        self.search()

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def on_window_tabs_switch_page(self, notebook, page, pagenum):
        if pagenum == 0:
            self.on_fact_selection_changed(self.fact_tree)
        elif pagenum == 1:
            self.get_widget('remove').set_sensitive(False)
            self.get_widget('edit').set_sensitive(False)


    def on_add_clicked(self, button):
        fact = self.fact_tree.get_selected_fact()
        if not fact:
            selected_date = self.start_date
        elif isinstance(fact, dt.date):
            selected_date = fact
        else:
            selected_date = fact["date"]

        dialogs.edit.show(fact_date = selected_date)

    def on_remove_clicked(self, button):
        self.overview.delete_selected()

    def on_edit_clicked(self, button):
        fact = self.fact_tree.get_selected_fact()
        if not fact or isinstance(fact, dt.date):
            return
        dialogs.edit.show(fact_id = fact["id"])

    def on_tabs_window_deleted(self, widget, event):
        self.close_window()

    def on_window_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w
              and event_key.state & gtk.gdk.CONTROL_MASK)):
        self.close_window()

    def close_window(self):
        runtime.dispatcher.del_handler('activity_updated', self.after_activity_update)
        runtime.dispatcher.del_handler('day_updated', self.after_activity_update)
        runtime.dispatcher.del_handler('conf_changed', self.on_conf_change)

        # properly saving window state and position
        maximized = self.window.get_window().get_state() & gtk.gdk.WINDOW_STATE_MAXIMIZED
        conf.set("overview_window_maximized", maximized)

        # make sure to remember dimensions only when in normal state
        if maximized == False and not self.window.get_window().get_state() & gtk.gdk.WINDOW_STATE_ICONIFIED:
            x, y = self.window.get_position()
            w, h = self.window.get_size()
            conf.set("overview_window_box", [x, y, w, h])


        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            return False

    def show(self):
        self.window.show()
