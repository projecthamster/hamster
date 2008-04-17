# - coding: utf-8 -

# Copyright (C) 2008 Toms Bauģis <toms.baugis at gmail.com>

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
import gtk
import pango

from hamster import dispatcher, storage, SHARED_DATA_DIR
from hamster.charting import Chart
from hamster.add_custom_fact import CustomFactController

import datetime  as dt
import calendar
import gobject

class StatsViewer:
    def __init__(self):
        self.glade = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, "stats.glade"))
        self.window = self.get_widget('stats_window')

        self.fact_tree = self.get_widget("facts")
        self.fact_tree.set_headers_visible(False)
        self.fact_tree.set_tooltip_column(1)
        self.fact_tree.set_property("show-expanders", False)

        nameColumn = gtk.TreeViewColumn(_("Name"))
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()
        nameCell.set_property("ellipsize", pango.ELLIPSIZE_END)
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_cell_data_func(nameCell, self.parent_painter)
        self.fact_tree.append_column(nameColumn)

        self.fact_tree.append_column(gtk.TreeViewColumn("", gtk.CellRendererText(), text=2))
        
        self.fact_store = gtk.TreeStore(int, str, str, str) #id, caption, duration, date (invisible)
        self.fact_tree.set_model(self.fact_store)
        
        x_offset = 80 # let's nicely align all graphs
        
        self.day_chart = Chart(max_bar_width = 40,
                               collapse_whitespace = True,
                               legend_width = x_offset)
        eventBox = gtk.EventBox()
        place = self.get_widget("totals_by_day")
        eventBox.add(self.day_chart);
        place.add(eventBox)
        
        self.category_chart = Chart(orient = "horizontal",
                                    max_bar_width = 30,
                                    animate=False,
                                    values_on_bars = True,
                                    stretch_grid = True,
                                    legend_width = x_offset)
        eventBox = gtk.EventBox()
        place = self.get_widget("totals_by_category")
        eventBox.add(self.category_chart);
        place.add(eventBox)
        
        self.activity_chart = Chart(orient = "horizontal",
                                    max_bar_width = 25,
                                    animate = False,
                                    values_on_bars = True,
                                    stretch_grid = True,
                                    legend_width = x_offset)
        eventBox = gtk.EventBox()
        place = self.get_widget("totals_by_activity")
        eventBox.add(self.activity_chart);
        place.add(eventBox)
        
        self.view_date = dt.date.today()
        self.start_date = self.view_date - dt.timedelta(self.view_date.weekday()) #set to monday
        self.end_date = self.start_date + dt.timedelta(6) #set to monday

        
        self.day_view = self.get_widget("day")
        self.week_view = self.get_widget("week")
        self.month_view = self.get_widget("month")

        self.week_view.set_group(self.day_view)
        self.month_view.set_group(self.day_view)
        
        #initiate the form in the week view
        self.week_view.set_active(True)


        dispatcher.add_handler('activity_updated', self.after_activity_update)
        dispatcher.add_handler('day_updated', self.after_fact_update)

        selection = self.fact_tree.get_selection()
        selection.connect('changed', self.on_fact_selection_changed, self.fact_store)

        self.glade.signal_autoconnect(self)
        self.fact_tree.grab_focus()
        self.do_graph()


        
    def format_duration(self, duration):
        if duration == None:
            return None
        
        hours = duration / 60
        days = hours / 24
        hours %= 24
        minutes = duration % 60
        formatted_duration = ""
        
        #TODO - convert to list comprehension or that other thing
        if days > 0:
            formatted_duration += "%d:" % days
        formatted_duration += "%02d:%02d" % (hours, minutes)
                
        return formatted_duration
    

    def parent_painter(self, column, cell, model, iter):
        cell_text = model.get_value(iter, 1)
        if model.iter_parent(iter) == None:
            if model.get_path(iter) == (0,):
                text = '<span weight="heavy">%s</span>' % cell_text
            else:
                text = '<span weight="heavy" rise="-20000">%s</span>' % cell_text
                
            cell.set_property('markup', text)

        else:
            cell.set_property('text', "   " + cell_text)
            
        return

    def get_facts(self):
        self.fact_store.clear()
        totals = {}
        
        by_activity = {}
        by_category = {}
        by_day = {}
        
        week = {"days": [], "totals": []}
        
        facts = storage.get_facts(self.start_date, self.end_date)
        
        for i in range((self.end_date - self.start_date).days  + 1):
            current_date = self.start_date + dt.timedelta(i)
            day_row = self.fact_store.append(None, [-1,
                                                    current_date.strftime('%A, %b %d.'),
                                                    "",
                                                    current_date.strftime('%Y-%m-%d')])
            by_day[self.start_date + dt.timedelta(i)] = {"duration": 0, "row_pointer": day_row}
        
        for fact in facts:
            start_date = fact["start_time"].date()
            
            duration = None
            if fact["end_time"]: # not set if just started
                delta = fact["end_time"] - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60

            self.fact_store.append(by_day[start_date]["row_pointer"],
                                   [fact["id"],
                                    fact["start_time"].strftime('%H:%M') + " " +
                                    fact["name"],
                                    self.format_duration(duration),
                                    fact["start_time"].strftime('%Y-%m-%d')
                                    ])
            
            if fact["name"] not in by_activity: by_activity[fact["name"]] = 0
            if fact["category"] not in by_category: by_category[fact["category"]] = 0

            if duration:
                by_day[start_date]["duration"] += duration
                by_activity[fact["name"]] += duration
                by_category[fact["category"]] += duration
            
        days = 7 if self.week_view.get_active() else 30


        date_sort = lambda a, b: (b[4] < a[4]) - (a[4] < b[4])
        totals["by_day"] = []

        for day in by_day:
            if (self.end_date - self.start_date).days < 20:
                strday = day.strftime('%a')
                totals["by_day"].append([strday, by_day[day]["duration"] / 60.0, None, None, day])
            else:
                strday = day.strftime('%d. %b')
                background = 7 if day.weekday() in [5, 6] else None
                totals["by_day"].append([strday, by_day[day]["duration"] / 60.0, None, background, day])
        totals["by_day"].sort(date_sort)
            
            
        duration_sort = lambda a, b: (a[1] < b[1]) - (b[1] < a[1])
        totals["by_activity"] = []
        for activity in by_activity:
            totals["by_activity"].append([activity, by_activity[activity] / 60.0])
        totals["by_activity"].sort(duration_sort)
        
        #now we will limit bars to 6 and sum everything else into others
        if len(totals["by_activity"]) > 12:
            other_total = 0.0

            for i in range(11, len(totals["by_activity"]) - 1):
                other_total += totals["by_activity"][i][1]
                
            totals["by_activity"] = totals["by_activity"][:11]
            totals["by_activity"].append([_("Other"), other_total, 1])
        totals["by_activity"].sort(duration_sort) #sort again, since maybe others summed is bigger
            
        totals["by_category"] = []
        for category in by_category:
            totals["by_category"].append([category, by_category[category] / 60.0])
        totals["by_category"].sort(duration_sort)
        

        self.fact_tree.expand_all()


        week["totals"] = totals
            
        return week
        

    def do_graph(self):
        if self.start_date.year != self.end_date.year:
            start_str = self.start_date.strftime('%B %d. %Y')
            end_str = self.end_date.strftime('%B %d. %Y')
        elif self.start_date.month != self.end_date.month:
            start_str = self.start_date.strftime('%B %d.')
            end_str = self.end_date.strftime('%B %d.')
        else:
            start_str = self.start_date.strftime('%B %d')
            end_str = self.end_date.strftime('%d, %Y')

        if self.day_view.get_active(): #single day is an exception
            label_text = _("Overview for %s") % (self.start_date.strftime('%B %d. %Y'))
            dayview_caption = _("Day")
        elif self.week_view.get_active():
            label_text = _("Overview for %s - %s") % (start_str, end_str)
            dayview_caption = _("Week")
        else:
            label_text = _("Overview for %s - %s") % (start_str, end_str)
            dayview_caption = _("Month")
        
        label = self.get_widget("overview_label")
        label.set_text(label_text)

        label2 = self.get_widget("dayview_caption")
        label2.set_markup("<b>%s</b>" % (dayview_caption))
        
        facts = self.get_facts()

        self.day_chart.plot(facts["totals"]["by_day"])
        self.category_chart.plot(facts["totals"]["by_category"])
        self.activity_chart.plot(facts["totals"]["by_activity"])





    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.glade.get_widget(name)

    def on_prev_clicked(self, button):
        if self.day_view.get_active():
            self.start_date -= dt.timedelta(1)
            self.end_date -= dt.timedelta(1)
        
        elif self.week_view.get_active():
            self.start_date -= dt.timedelta(7)
            self.end_date -= dt.timedelta(7)
        
        elif self.month_view.get_active():
            self.end_date = self.start_date - dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.end_date.year, self.end_date.month)
            self.start_date = self.end_date - dt.timedelta(days_in_month - 1)

        self.view_date = self.start_date        
        self.do_graph()

    def on_next_clicked(self, button):
        if self.day_view.get_active():
            self.start_date += dt.timedelta(1)
            self.end_date += dt.timedelta(1)
        
        elif self.week_view.get_active():
            self.start_date += dt.timedelta(7)
            self.end_date += dt.timedelta(7)
        
        elif self.month_view.get_active():
            self.start_date = self.end_date + dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.start_date.year, self.start_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
        
        self.view_date = self.start_date
        self.do_graph()
    
    def on_home_clicked(self, button):
        self.view_date = dt.date.today()
        if self.day_view.get_active():
            self.start_date = self.view_date
            self.end_date = self.view_date
        
        elif self.week_view.get_active():
            self.start_date = self.view_date - dt.timedelta(self.view_date.weekday()) #set to monday
            self.end_date = self.start_date + dt.timedelta(6)
        
        elif self.month_view.get_active():
            self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
            first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1) #set to monday
        
        self.do_graph()
        
    def on_day_toggled(self, button):
        self.start_date = self.view_date
        self.end_date = self.view_date
        self.do_graph()

    def on_week_toggled(self, button):
        self.start_date = self.view_date - dt.timedelta(self.view_date.weekday()) #set to monday
        self.end_date = self.start_date + dt.timedelta(6)
        self.do_graph()

        
    def on_month_toggled(self, button):
        self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
        first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
        self.end_date = self.start_date + dt.timedelta(days_in_month - 1) #set to monday

        self.do_graph()
        
    def on_remove_clicked(self, button):
        self.delete_selected()

    def delete_selected(self):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        if model[iter][0] == -1:
            return #not a fact

        next_row = model.iter_next(iter)

        if next_row:
            selection.select_iter(next_row)
        else:
            path = model.get_path(iter)[0] - 1
            if path > 0:
                selection.select_path(path)

        storage.remove_fact(model[iter][0])

    """keyboard events"""
    def on_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Delete):
        self.delete_selected()
    
    def on_fact_selection_changed(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()

        id = -1
        if iter:
            id = model[iter][0]

        self.get_widget('remove').set_sensitive(id != -1)

        return True
        
    def on_add_clicked(self, button):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        selected_date = self.view_date
        if iter:
            selected_date = model[iter][3].split("-")
            selected_date = dt.date(int(selected_date[0]),
                                    int(selected_date[1]),
                                    int(selected_date[2]))

        custom_fact = CustomFactController(selected_date)
        custom_fact.show()

    def after_activity_update(self, widget, renames):
        self.do_graph()
    
    def after_fact_update(self, event, date):
        self.do_graph()
        
    def on_close(self, widget, event):
        dispatcher.del_handler('activity_updated', self.after_activity_update)
        dispatcher.del_handler('day_updated', self.after_fact_update)
        return False

    def on_window_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Escape):
        self.window.destroy()
    
    def show(self):
        self.window.show_all()

