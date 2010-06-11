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

        self.fact_tree.connect("button-press-event", self.on_fact_tree_button_press)

        self.reports = TotalsBox()
        self.get_widget("reports_tab").add(self.reports)

        self.current_range = "week"

        self.timechart = widgets.TimeChart()
        self.timechart.day_start = self.day_start

        self.get_widget("by_day_box").add(self.timechart)

        self._gui.connect_signals(self)
        runtime.storage.connect('activities-changed',self.after_activity_update)
        runtime.storage.connect('facts-changed',self.after_activity_update)

        conf.connect('conf-changed', self.on_conf_change)

        #self.get_widget("hbox1").pack_start(gtk.VSeparator())
        self.get_widget("hbox1").pack_start(gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_ETCHED_IN))

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


    def on_fact_tree_button_press(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.get_widget("fact_tree_popup").popup( None, None, None, event.button, time)
            return True

    def search(self):
        if self.start_date > self.end_date: # make sure the end is always after beginning
            self.start_date, self.end_date = self.end_date, self.start_date

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
        self.title = self.format_range(self.start_date, self.end_date)
        self.window.set_title(self.title.decode("utf-8"))
        self.get_widget("range_title").set_text(self.title)


    def format_range(self, start_date, end_date):
        dates_dict = stuff.dateDict(start_date, "start_")
        dates_dict.update(stuff.dateDict(end_date, "end_"))

        if start_date == end_date:
            # Overview label if looking on single day
            # date format for overview label when only single day is visible
            # Using python datetime formatting syntax. See:
            # http://docs.python.org/library/time.html#time.strftime
            title = start_date.strftime(_("%B %d, %Y"))
        elif start_date.year != end_date.year:
            # overview label if start and end years don't match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            title = _(u"%(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif start_date.month != end_date.month:
            # overview label if start and end month do not match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            title = _(u"%(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        else:
            # overview label for interval in same month
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            # see http://docs.python.org/library/time.html#time.strftime
            title = _(u"%(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict

        return title

    def on_conf_change(self, event, key, value):
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

    def after_activity_update(self, widget):
        self.search()

    def on_search_icon_press(self, widget, position, data):
        if position == gtk.ENTRY_ICON_SECONDARY:
            widget.set_text('')

        self.search()

    def on_search_activate(self, widget):
        self.search()

    def on_search_changed(self, widget):
        has_text = len(widget.get_text()) > 0
        widget.set_icon_sensitive(gtk.ENTRY_ICON_SECONDARY, has_text)

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


    def apply_range_select(self):
        self.get_widget("range_popup").hide()
        self.get_widget("date_pick").set_active(False)
        self.search()

    def on_day_activate(self, button):
        self.current_range = "day"
        self.start_date = self.view_date
        self.end_date = self.start_date + dt.timedelta(0)
        self.apply_range_select()

    def on_week_activate(self, button):
        self.current_range = "week"
        self.start_date, self.end_date = self.week()
        self.apply_range_select()

    def on_month_activate(self, button):
        self.current_range = "month"
        self.start_date, self.end_date = self.month()
        self.apply_range_select()

    def on_manual_range_apply_clicked(self, button):
        self.current_range = "manual"
        cal_date = self.get_widget("start_calendar").get_date()
        self.start_date = dt.date(cal_date[0], cal_date[1] + 1, cal_date[2])

        cal_date = self.get_widget("end_calendar").get_date()
        self.end_date = dt.date(cal_date[0], cal_date[1] + 1, cal_date[2])

        self.apply_range_select()




    def week(self):
        # aligns start and end date to week
        start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
        start_date = start_date + dt.timedelta(stuff.locale_first_weekday())
        end_date = start_date + dt.timedelta(6)
        return start_date, end_date

    def month(self):
        # aligns start and end date to month
        start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
        first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
        end_date = start_date + dt.timedelta(days_in_month - 1)
        return start_date, end_date


    def on_tabs_window_configure_event(self, window, event):
        # this is required so that the rows would grow on resize
        self.fact_tree.fix_row_heights()


    def on_start_date_entered(self, input):
        self.start_date = input.get_date()
        self.view_date = self.start_date
        self.search()

    def on_end_date_entered(self, input):
        self.end_date = input.get_date()
        self.search()


    def on_prev_activate(self, action):
        if self.current_range == "day":
            self.start_date -= dt.timedelta(1)
            self.end_date -= dt.timedelta(1)
        elif self.current_range == "week":
            self.start_date -= dt.timedelta(7)
            self.end_date -= dt.timedelta(7)
        elif self.current_range == "month":
            self.end_date = self.start_date - dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.end_date.year, self.end_date.month)
            self.start_date = self.end_date - dt.timedelta(days_in_month - 1)
        else:
            # manual range - just jump to the next window
            days =  (self.end_date - self.start_date) + dt.timedelta(days = 1)
            self.start_date = self.start_date - days
            self.end_date = self.end_date - days

        self.view_date = self.start_date
        self.search()

    def on_next_activate(self, action):
        if self.current_range == "day":
            self.start_date += dt.timedelta(1)
            self.end_date += dt.timedelta(1)
        elif self.current_range == "week":
            self.start_date += dt.timedelta(7)
            self.end_date += dt.timedelta(7)
        elif self.current_range == "month":
            self.start_date = self.end_date + dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.start_date.year, self.start_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
        else:
            # manual range - just jump to the next window
            days =  (self.end_date - self.start_date) + dt.timedelta(days = 1)
            self.start_date = self.start_date + days
            self.end_date = self.end_date + days

        self.view_date = self.start_date
        self.search()


    def on_home_activate(self, action):
        self.view_date = (dt.datetime.today() - dt.timedelta(hours = self.day_start.hour,
                                                        minutes = self.day_start.minute)).date()
        if self.current_range == "day":
            self.start_date = self.view_date
            self.end_date = self.start_date + dt.timedelta(0)

        elif self.current_range == "week":
            self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
            self.start_date = self.start_date + dt.timedelta(stuff.locale_first_weekday())
            self.end_date = self.start_date + dt.timedelta(6)
        elif self.current_range == "month":
            self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
            first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
        else:
            days =  (self.end_date - self.start_date)
            self.start_date = self.view_date
            self.end_date = self.view_date + days

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
            self.reports.do_charts()


    def on_add_activate(self, action):
        fact = self.fact_tree.get_selected_fact()
        if not fact:
            selected_date = self.start_date
        elif isinstance(fact, dt.date):
            selected_date = fact
        else:
            selected_date = fact["date"]

        dialogs.edit.show(fact_date = selected_date)

    def on_remove_activate(self, button):
        self.overview.delete_selected()


    def on_date_pick_toggled(self, button):
        if button.get_active():
            popup = self.get_widget("range_popup")


            window = button.get_window()
            x, y = window.get_origin()

            alloc = button.get_allocation()

            popup.move(x + alloc.x,y + alloc.y + alloc.height)

            self.get_widget("day_preview").set_text(self.format_range(self.view_date, self.view_date).decode("utf-8"))
            self.get_widget("week_preview").set_text(self.format_range(*self.week()).decode("utf-8"))
            self.get_widget("month_preview").set_text(self.format_range(*self.month()).decode("utf-8"))

            start_cal = self.get_widget("start_calendar")
            start_cal.select_month(self.start_date.month, self.start_date.year)
            start_cal.select_day(self.start_date.day)

            end_cal = self.get_widget("end_calendar")
            end_cal.select_month(self.end_date.month, self.end_date.year)
            end_cal.select_day(self.end_date.day)

            popup.show_all()
        else:
            self.get_widget("range_popup").hide()

    def on_edit_activate(self, button):
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
