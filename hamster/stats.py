#!/usr/bin/env python
import pygtk
pygtk.require('2.0')

import os
import gtk
import gtk.glade

from hamster import dispatcher, storage, SHARED_DATA_DIR
from hamster.charting import Chart
from hamster.add_custom_fact import CustomFactController

import datetime  as dt
import calendar
import gobject

class StatsViewer:
    def __init__(self):
        self.wTree = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, "stats.glade"))
        self.window = self.get_widget('stats_window')

        self.fact_store = gtk.TreeStore(int, str, str)
            

        self.fact_tree = self.get_widget("facts")
        self.fact_tree.set_headers_visible(False)

        nameColumn = gtk.TreeViewColumn(_(u'Name'))
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_attributes(nameCell, text=1)
        self.fact_tree.append_column(nameColumn)

        durationColumn = gtk.TreeViewColumn(' ')
        durationColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        durationColumn.set_expand(False)
        durationCell = gtk.CellRendererText()
        durationColumn.pack_start(durationCell, True)
        durationColumn.set_attributes(durationCell, text=2)
        self.fact_tree.append_column(durationColumn)
        
        self.fact_tree.set_model(self.fact_store)
        
        self.day_chart = Chart(max_bar_width = 40,
                               collapse_whitespace = True)
        eventBox = gtk.EventBox()
        place = self.get_widget("totals_by_day")
        eventBox.add(self.day_chart);
        place.add(eventBox)
        
        self.category_chart = Chart(orient = "horizontal",
                                    max_bar_width = 30,
                                    animate=False,
                                    values_on_bars = True)
        eventBox = gtk.EventBox()
        place = self.get_widget("totals_by_category")
        eventBox.add(self.category_chart);
        place.add(eventBox)
        
        self.activity_chart = Chart(orient = "horizontal",
                                    max_bar_width = 20,
                                    animate = False,
                                    values_on_bars = True)
        eventBox = gtk.EventBox()
        place = self.get_widget("totals_by_activity")
        eventBox.add(self.activity_chart);
        place.add(eventBox)
        
        self.start_date = dt.date.today()
        self.start_date = self.start_date - dt.timedelta(self.start_date.weekday()) #set to monday
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

        self.wTree.signal_autoconnect(self)
        self.do_graph()


        
    def format_duration(self, duration):
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
    

    def get_facts(self):
        self.fact_store.clear()
        totals = {}
        
        by_activity = {}
        by_category = {}
        by_day = {}
        
        week = {"days": [], "totals": []}
        
        facts = storage.get_facts(self.start_date, self.end_date)
        
        for i in range((self.end_date - self.start_date).days  + 1):
            day_row = self.fact_store.append(None, [-1,
                                                    (self.start_date + dt.timedelta(i)).strftime('%A, %b %d.'), ""])
            by_day[self.start_date + dt.timedelta(i)] = {"duration": 0, "row_pointer": day_row}
        
        for fact in facts:
            start_date = fact["start_time"].date()
            
            if fact["end_time"]: # not set if just started
                delta = fact["end_time"] - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60

                self.fact_store.append(by_day[start_date]["row_pointer"],
                                       [fact["id"],
                                        fact["start_time"].strftime('%H:%M') + " " +
                                        fact["name"],
                                        self.format_duration(duration)])
                
                if fact["name"] not in by_activity: by_activity[fact["name"]] = 0
                if fact["category"] not in by_category: by_category[fact["category"]] = 0

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
            
            
        duration_sort = lambda a, b: int(b[1] - a[1])
        totals["by_activity"] = []
        for activity in by_activity:
            totals["by_activity"].append([activity, by_activity[activity] / 60.0])
        totals["by_activity"].sort(duration_sort)
            
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
            label_text = "Overview for %s" % (self.start_date.strftime('%B %d. %Y'))
        else:
            label_text = "Overview for %s - %s" % (start_str, end_str)
        
        label = self.get_widget("overview_label")
        label.set_text(label_text)
        
        facts = self.get_facts()

        self.day_chart.plot(facts["totals"]["by_day"])
        self.category_chart.plot(facts["totals"]["by_category"])
        self.activity_chart.plot(facts["totals"]["by_activity"])





    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.wTree.get_widget(name)

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
        
        self.do_graph()
    
    def on_home_clicked(self, button):
        self.start_date = dt.date.today()
        if self.day_view.get_active():
            self.end_date = self.start_date
        
        elif self.week_view.get_active():
            self.start_date = self.start_date - dt.timedelta(self.start_date.weekday()) #set to monday
            self.end_date = self.start_date + dt.timedelta(6)
        
        elif self.month_view.get_active():
            self.start_date = self.start_date - dt.timedelta(self.start_date.day - 1) #set to beginning of month
            first_weekday, days_in_month = calendar.monthrange(self.start_date.year, self.start_date.month)
            self.end_date = self.start_date + dt.timedelta(days_in_month - 1) #set to monday
        
        self.do_graph()
        
    def on_day_toggled(self, button):
        self.end_date = self.start_date
        self.do_graph()

    def on_week_toggled(self, button):
        self.start_date = self.start_date - dt.timedelta(self.start_date.weekday()) #set to monday
        self.end_date = self.start_date + dt.timedelta(6)
        self.do_graph()

        
    def on_month_toggled(self, button):
        self.start_date = self.start_date - dt.timedelta(self.start_date.day - 1) #set to beginning of month
        first_weekday, days_in_month = calendar.monthrange(self.start_date.year, self.start_date.month)
        self.end_date = self.start_date + dt.timedelta(days_in_month - 1) #set to monday

        self.do_graph()
        
    def on_remove_clicked(self, button):
        self.delete_selected()

    def delete_selected(self):
        selection = self.fact_tree.get_selection()
        (model, iter) = selection.get_selected()

        next_row = model.iter_next(iter)

        if next_row:
            selection.select_iter(next_row)
        else:
            path = model.get_path(iter)[0] - 1
            if path > 0:
                selection.select_path(path)

        storage.remove_fact(model[iter][0])
        model.remove(iter)

    def on_fact_selection_changed(self, selection, model):
        """ enables and disables action buttons depending on selected item """
        (model, iter) = selection.get_selected()

        id = -1
        if iter:
            id = model[iter][0]

        self.get_widget('remove').set_sensitive(id != -1)

        return True
        
    def on_add_clicked(self, button):
        #date = selected_date.strftime('%Y%m%d')

        custom_fact = CustomFactController()
        custom_fact.show()

    def after_activity_update(self, widget, renames):
        self.do_graph()
    
    def after_fact_update(self, event, date):
        self.do_graph()
    
    def show(self):
        self.window.show_all()

