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
from configuration import runtime, GconfStore, dialogs
import widgets, reports

from stats_overview import OverviewBox
from stats_reports import ReportsBox

class StatsViewer(object):
    def __init__(self, parent = None):
        self.parent = parent# determine if app should shut down on close
        self._gui = stuff.load_ui_file("stats.ui")
        self.report_chooser = None
        
        self.facts = None

        self.window = self.get_widget("tabs_window")

        self.config = GconfStore()
        self.day_start = self.config.get_day_start()

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

        self.reports = ReportsBox()
        self.get_widget("reports_tab").add(self.reports)
        
        self.range_combo = gtk.combo_box_new_text()
        self.range_combo.append_text(_("Week"))
        self.range_combo.append_text(_("Month"))
        self.range_combo.append_text(_("Date Range"))
        self.range_combo.set_row_separator_func(lambda row, iter: row[iter][0] == "-")
        self.range_combo.append_text("-")
        self.range_combo.append_text("All")
        self.range_combo.set_active(0)
        self.range_combo.connect("changed", self.on_range_combo_changed)
        
        
        
        self.get_widget("range_pick").add(self.range_combo)


        self.start_date_input = widgets.DateInput(self.start_date)
        self.start_date_input.connect("date-entered", self.on_start_date_entered)
        self.get_widget("range_start_box").add(self.start_date_input)

        self.end_date_input = widgets.DateInput(self.end_date)
        self.end_date_input.connect("date-entered", self.on_end_date_entered)
        self.get_widget("range_end_box").add(self.end_date_input)

        self.timeline = widgets.TimeLine()
        self.get_widget("by_day_box").add(self.timeline)

        self._gui.connect_signals(self)
        runtime.dispatcher.add_handler('activity_updated', self.after_activity_update)
        runtime.dispatcher.add_handler('day_updated', self.after_activity_update)


        self.window.show_all()
        self.search()

    def on_fact_selection_changed(self, tree):
        """ enables and disables action buttons depending on selected item """
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()

        id = -1
        if iter:
            id = model[iter][0]

        self.get_widget('remove').set_sensitive(id != -1)
        self.get_widget('edit').set_sensitive(id != -1)

        return True

    def after_activity_update(self, widget, renames):
        self.search()

    def search(self):
        if self.start_date > self.end_date: # make sure the end is always after beginning
            self.start_date, self.end_date = self.end_date, self.start_date
        
        self.start_date_input.set_date(self.start_date)
        self.end_date_input.set_date(self.end_date)
        
        search_terms = self.get_widget("search").get_text().decode("utf8", "replace")
        self.facts = runtime.storage.get_facts(self.start_date, self.end_date, search_terms)

        self.get_widget("report_button").set_sensitive(len(self.facts) > 0)

        self.timeline.draw(self.facts, self.start_date, self.end_date)


        if self.get_widget("window_tabs").get_current_page() == 0:
            self.overview.search(self.start_date, self.end_date, self.facts)
            self.reports.search(self.start_date, self.end_date, self.facts)
        else:
            self.reports.search(self.start_date, self.end_date, self.facts)
            self.overview.search(self.start_date, self.end_date, self.facts)

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
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        selected_date = self.view_date
        if iter and model[iter][6]: # TODO - here we should check if heading maybe specifies a date
            selected_date = model[iter][6]["date"]

        dialogs.edit.show(fact_date = selected_date)

    def on_remove_clicked(self, button):
        self.delete_selected()

    def on_edit_clicked(self, button):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        if model[iter][0] == -1:
            return #not a fact

        dialogs.edit.show(fact_id = model[iter][0])


    def on_close(self, widget, event):
        runtime.dispatcher.del_handler('activity_updated', self.after_activity_update)
        runtime.dispatcher.del_handler('day_updated', self.after_fact_update)
        self.close_window()        

    def on_window_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w 
              and event_key.state & gtk.gdk.CONTROL_MASK)):
        self.close_window()
    
    
    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            return False
        
    def show(self):
        self.window.show()

