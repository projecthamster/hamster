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

from hamster import dispatcher, storage, SHARED_DATA_DIR, stuff
from hamster.charting import Chart
from hamster.add_custom_fact import CustomFactController

import datetime as dt
import calendar
import gobject
import time

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

        timeColumn = gtk.TreeViewColumn(_("Duration"))
        timeCell = gtk.CellRendererText()
        timeColumn.pack_end(timeCell, True)
        timeColumn.set_cell_data_func(timeCell, self.duration_painter)
        self.fact_tree.append_column(timeColumn)
        
        self.fact_store = gtk.TreeStore(int, str, str, str, str) #id, caption, duration, date (invisible), description
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
        
        self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1) #set to monday
        # look if we need to start on sunday or monday
        self.start_date = self.start_date + dt.timedelta(self.locale_first_weekday())
        
        self.end_date = self.start_date + dt.timedelta(6)

        
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

    def locale_first_weekday(self):
        """figure if week starts on monday or sunday"""
        import os
        first_weekday = 6 #by default settle on monday

        try:
            process = os.popen("locale first_weekday week-1stday")
            week_offset, week_start = process.read().split('\n')[:2]
            process.close()
            week_start = dt.date(*time.strptime(week_start, "%Y%m%d")[:3])
            week_offset = dt.timedelta(int(week_offset) - 1)
            beginning = week_start + week_offset
            first_weekday = int(beginning.strftime("%w"))
        except:
            print "WARNING - Failed to get first weekday from locale"
            pass
            
        return first_weekday
        
    def parent_painter(self, column, cell, model, iter):
        cell_text = model.get_value(iter, 1)
        if model.iter_parent(iter) == None:
            if model.get_path(iter) == (0,):
                text = '<span weight="heavy">%s</span>' % cell_text
            else:
                text = '<span weight="heavy" rise="-20000">%s</span>' % cell_text
                
            cell.set_property('markup', text)

        else:
            activity_name = cell_text
            description = model.get_value(iter, 4)
    
            text = "   %s" % activity_name
            if description:
                text+= """\n             <span style="italic" size="small">%s</span>""" % (description)
                
            cell.set_property('markup', text)

    def duration_painter(self, column, cell, model, iter):
        text = model.get_value(iter, 2)
        if model.iter_parent(iter) == None:
            if model.get_path(iter) == (0,):
                text = '<span weight="heavy">%s</span>' % text
            else:
                text = '<span weight="heavy" rise="-20000">%s</span>' % text
        cell.set_property('markup', text)

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
            # date format in overview window fact listing
            # prefix is "o_",letter after prefix is regular python format. you can use all of them
            fact_date = _("%(o_A)s, %(o_b)s %(o_d)s") %  stuff.dateDict(current_date, "o_")

            day_row = self.fact_store.append(None, [-1,
                                                    fact_date,
                                                    "",
                                                    current_date.strftime('%Y-%m-%d'),
                                                    ""])
            by_day[self.start_date + dt.timedelta(i)] = {"duration": 0, "row_pointer": day_row}

        for fact in facts:
            start_date = fact["start_time"].date()

            duration = None
            if fact["end_time"]: # not set if just started
                delta = fact["end_time"] - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60
            elif fact["start_time"].date() == dt.date.today():
                delta = dt.datetime.now() - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60

            self.fact_store.append(by_day[start_date]["row_pointer"],
                                   [fact["id"],
                                    fact["start_time"].strftime('%H:%M') + " " +
                                    fact["name"],
                                    stuff.format_duration(duration),
                                    fact["start_time"].strftime('%Y-%m-%d'),
                                    fact["description"]
                                    ])

            if fact["name"] not in by_activity: by_activity[fact["name"]] = 0
            if fact["category"] not in by_category: by_category[fact["category"]] = 0

            if duration:
                by_day[start_date]["duration"] += duration
                by_activity[fact["name"]] += duration
                by_category[fact["category"]] += duration

        days = 30
        if self.week_view.get_active():
            days = 7


        date_sort = lambda a, b: (b[4] < a[4]) - (a[4] < b[4])
        totals["by_day"] = []

        for day in by_day:
            self.fact_store.set_value(by_day[day]["row_pointer"], 2,
                stuff.format_duration(by_day[day]["duration"]))
            if (self.end_date - self.start_date).days < 20:
                strday = stuff.locale_to_utf8(day.strftime('%a'))
                totals["by_day"].append([strday, by_day[day]["duration"] / 60.0, None, None, day])
            else:
                # date format in month chart in overview window (click on "month" to see it)
                # prefix is "m_", letter after prefix is regular python format. you can use all of them
                strday = _("%(m_b)s %(m_d)s") %  stuff.dateDict(day, "m_")

                background = None
                if day.weekday() in [5, 6]:
                    background = 7

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
        
        self.get_widget("report_button").set_sensitive(len(facts) > 0)


        week["totals"] = totals
            
        return week
        

    def do_graph(self):
        dates_dict = stuff.dateDict(self.start_date, "start_")
        dates_dict.update(stuff.dateDict(self.end_date, "end_"))
        
        
        if self.start_date.year != self.end_date.year:
            # overview label if start and end years don't match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            overview_label = _(u"Overview for %(start_B)s %(start_d)s, %(start_Y)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        elif self.start_date.month != self.end_date.month:
            #overview label if start and end month do not match
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            overview_label = _(u"Overview for %(start_B)s %(start_d)s – %(end_B)s %(end_d)s, %(end_Y)s") % dates_dict
        else:
            #overview label for interval in same month
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            overview_label = _(u"Overview for %(start_B)s %(start_d)s – %(end_d)s, %(end_Y)s") % dates_dict

        if self.day_view.get_active():
            # overview label for single day
            # letter after prefixes (start_, end_) is the one of
            # standard python date formatting ones- you can use all of them
            overview_label = _("Overview for %(start_B)s %(start_d)s, %(start_Y)s") % dates_dict
            dayview_caption = _("Day")
        elif self.week_view.get_active():
            dayview_caption = _("Week")
        else:
            dayview_caption = _("Month")
        
        
        label = self.get_widget("overview_label")
        label.set_text(overview_label)

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
            self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
            self.start_date = self.start_date + dt.timedelta(self.locale_first_weekday())
            self.end_date = self.start_date + dt.timedelta(6)
        
        elif self.month_view.get_active():
            self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
            first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1)
        
        self.do_graph()
        
    def on_day_toggled(self, button):
        self.start_date = self.view_date
        self.end_date = self.view_date
        self.do_graph()

    def on_week_toggled(self, button):
        self.start_date = self.view_date - dt.timedelta(self.view_date.weekday() + 1)
        self.start_date = self.start_date + dt.timedelta(self.locale_first_weekday())

        self.end_date = self.start_date + dt.timedelta(6)
        self.do_graph()

        
    def on_month_toggled(self, button):
        self.start_date = self.view_date - dt.timedelta(self.view_date.day - 1) #set to beginning of month
        first_weekday, days_in_month = calendar.monthrange(self.view_date.year, self.view_date.month)
        self.end_date = self.start_date + dt.timedelta(days_in_month - 1)

        self.do_graph()
        
    def on_remove_clicked(self, button):
        self.delete_selected()

    def on_edit_clicked(self, button):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        if model[iter][0] == -1:
            return #not a fact

        custom_fact = CustomFactController(None, model[iter][0])
        custom_fact.show()

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
        self.get_widget('edit').set_sensitive(id != -1)

        return True

    def on_facts_row_activated(self, tree, path, column):
        selection = tree.get_selection()
        (model, iter) = selection.get_selected()
        custom_fact = CustomFactController(None, model[iter][0])
        custom_fact.show()
        
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
        
    def on_report_button_clicked(self, widget):
        from hamster import reports
        facts = storage.get_facts(self.start_date, self.end_date)
        reports.simple(facts, self.start_date, self.end_date)

    def after_activity_update(self, widget, renames):
        self.do_graph()
    
    def after_fact_update(self, event, date):
        self.do_graph()
        
    def on_close(self, widget, event):
        dispatcher.del_handler('activity_updated', self.after_activity_update)
        dispatcher.del_handler('day_updated', self.after_fact_update)
        return False

    def on_window_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w 
              and event_key.state & gtk.gdk.CONTROL_MASK)):
        self.window.destroy()
    
    def show(self):
        self.window.show_all()

