#!/usr/bin/env python
import pygtk
pygtk.require('2.0')

import os
import gtk
import gtk.glade

from hamster import dispatcher, storage, SHARED_DATA_DIR
from hamster.charting import Chart

import datetime  as dt

class StatsViewer:
    def __init__(self):
        self.wTree = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, "stats.glade"))
        self.window = self.get_widget('stats_window')

        self.today = dt.datetime.today()
        self.monday = self.today - dt.timedelta(self.today.weekday())


        self.fact_store = gtk.TreeStore(str, str)
            

        self.fact_tree = self.get_widget("facts")
        self.fact_tree.set_headers_visible(False)

        nameColumn = gtk.TreeViewColumn(_(u'Name'))
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_attributes(nameCell, text=0)
        self.fact_tree.append_column(nameColumn)

        durationColumn = gtk.TreeViewColumn(' ')
        durationColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        durationColumn.set_expand(False)
        durationCell = gtk.CellRendererText()
        durationColumn.pack_start(durationCell, True)
        durationColumn.set_attributes(durationCell, text=1)
        self.fact_tree.append_column(durationColumn)
        
        self.fact_tree.set_model(self.fact_store)
        
        self.wTree.signal_autoconnect(self)

        self.day_chart = Chart(max_bar_width = 40, collapse_whitespace = True)
        eventBox = gtk.EventBox()
        place = self.get_widget("totals_by_day")
        eventBox.add(self.day_chart);
        place.add(eventBox)
        
        self.category_chart = Chart(orient = "horizontal", max_bar_width = 30, animate=False)
        eventBox = gtk.EventBox()
        place = self.get_widget("totals_by_category")
        eventBox.add(self.category_chart);
        place.add(eventBox)
        
        self.activity_chart = Chart(orient = "horizontal", max_bar_width = 20, animate=False)
        eventBox = gtk.EventBox()
        place = self.get_widget("totals_by_activity")
        eventBox.add(self.activity_chart);
        place.add(eventBox)
        
        
        self.day_view = self.get_widget("day")
        self.week_view = self.get_widget("week")
        self.month_view = self.get_widget("month")

        self.week_view.set_group(self.day_view)
        self.month_view.set_group(self.day_view)
        
        self.week_view.set_active(True)
        
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
        
        totals['by_day'] = []
        by_activity = {}
        by_category = {}
        
        week = {"days": [], "totals": []}
        
        #TODO make more readable
        days = 7 if self.week_view.get_active() else 30
        
        for i in range(days):
            current_date = self.monday + dt.timedelta(i)
            strdate = current_date.strftime('%A, %b %d.')
            facts = storage.get_facts(current_date)
            
            day_row = self.fact_store.append(None, [strdate, ""])
            day_total = 0

            for fact in facts:
                if fact["end_time"]: # not set if just started
                    delta = fact["end_time"] - fact["start_time"]
                    duration = 24 * delta.days + delta.seconds / 60

                    self.fact_store.append(day_row, [fact["name"], self.format_duration(duration)])
                    
                    if fact["name"] not in by_activity: by_activity[fact["name"]] = 0
                    if fact["category"] not in by_category: by_category[fact["category"]] = 0

                    by_activity[fact["name"]] += duration
                    by_category[fact["category"]] += duration
                    day_total += duration

            strday = current_date.strftime('%a') if days < 20 else current_date.strftime('%d. %b')

            totals['by_day'].append([strday, day_total / 60])
        
        totals["by_category"] = []
        for category in by_category:
            totals["by_category"].append([category, by_category[category] / 60])
            
        totals["by_activity"] = []
        for activity in by_activity:
            totals["by_activity"].append([activity, by_activity[activity] / 60])
            
        duration_sort = lambda a, b: b[1] - a[1]
        
        totals["by_category"].sort(duration_sort)
        totals["by_activity"].sort(duration_sort)
        

        self.fact_tree.expand_all()


        week["totals"] = totals
            
        return week
        

    def do_graph(self):
        facts = self.get_facts()

        self.day_chart.plot(facts["totals"]["by_day"])
        self.category_chart.plot(facts["totals"]["by_category"])
        self.activity_chart.plot(facts["totals"]["by_activity"])





    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.wTree.get_widget(name)

    def on_prev_clicked(self, button):
        self.monday -= dt.timedelta(7)
        self.do_graph()

    def on_next_clicked(self, button):
        self.monday += dt.timedelta(7)
        self.do_graph()
    
    def on_home_clicked(self, button):
        self.today = dt.datetime.today()
        self.monday = self.today - dt.timedelta(self.today.weekday())
        self.do_graph()
        
    def on_day_toggled(self, button):
        self.do_graph()
        
    def on_week_toggled(self, button):
        self.do_graph()
        
    def on_month_toggled(self, button):
        self.do_graph()
        
    
    
    def show(self):
        self.window.show_all()

