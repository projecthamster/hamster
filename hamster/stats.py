#!/usr/bin/env python
import pygtk
pygtk.require('2.0')

import os
import gtk
import gtk.glade

from hamster import dispatcher, storage, SHARED_DATA_DIR

import matplotlib
import datetime  as dt
matplotlib.use('gtkAgg')
from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
from matplotlib import rc
from matplotlib.figure import Figure
import matplotlib.dates
from matplotlib.dates import drange, DateFormatter, DayLocator, MonthLocator, YearLocator, date2num


#some hand-picked tango colors
color_list = [
    "#edd400", "#f57900", "#c17d11", "#73d216", "#3465a4", "#75507b", "#cc0000",
    "#fcaf3e", "#e9b96e", "#8ae234", "#729fcf", "#ad7fa8", "#ef2929",
    "#c4a000", "#ce5c00", "#8f5902", "#4e9a06", "#204a87", "#5c3566", "a40000"
]

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
    

    def get_week(self):
        self.fact_store.clear()
        totals = {}
        
        totals['by_day'] = {}
        totals['by_activity'] = {}
        totals['by_category'] = {}
        
        week = {"days": [], "totals": []}
            
        for i in range(7):
            current_date = self.monday + dt.timedelta(i)
            strdate = current_date.strftime('%A, %b %d.')
            facts = storage.get_facts(current_date)
            
            day_row = self.fact_store.append(None, [strdate, ""])

            for fact in facts:
                if fact["end_time"]: # not set if just started
                    delta = fact["end_time"] - fact["start_time"]
                    duration = 24 * delta.days + delta.seconds / 60

                    self.fact_store.append(day_row, [fact["name"], self.format_duration(duration)])
                    
                    if i not in totals['by_day']: totals['by_day'][i] = 0
                    if fact["name"] not in totals['by_activity']: totals['by_activity'][fact["name"]] = 0
                    if fact["category"] not in totals['by_category']: totals['by_category'][fact["category"]] = 0

                    totals['by_day'][i] += duration
                    totals['by_activity'][fact["name"]] += duration
                    totals['by_category'][fact["category"]] += duration

            week["days"].append({"date": current_date, "strdate": strdate, "facts": facts})
            

        self.fact_tree.expand_all()


        week["totals"] = totals
            
        return week
        

    def get_totals(self):
        totals = []

        for i in range(7):
            current_date = self.monday + dt.timedelta(i)
            numdate = current_date.strftime('%a')

            total = 0
            
            facts = storage.get_facts(current_date)
            
            for fact in facts:
                if fact["end_time"]: # not set if just started
                    delta = fact["end_time"] - fact["start_time"]
                    duration = 24 * delta.days + delta.seconds / 60
                    total += duration
            
            totals.append({'date': numdate, 'num': i, 'hours': total / 60}) #convert to hours
            
        return totals        
        

    def do_graph(self):


        week = self.get_week()
        



        fig = Figure()

        category_totals = week["totals"]["by_category"]
        
        # The numbers here are margins from the edge of the graph
        # You may need to adjust this depending on how you want your
        # graph to look, and how large your labels are
        ax = fig.add_axes([0.5, 0.1, 0.45, 0.8])
        
        i = 0
        labels = {}
        for category in category_totals:
            ax.barh(i, category_totals[category] / 60, color=color_list[i])
            labels[i] = category
            i = i + 1


        ax.set_yticks(range(len(category_totals)+1))
        ax.set_yticklabels(labels, va="bottom")
        

        self.canvas = FigureCanvas(fig) # a gtk.DrawingArea   
        self.canvas.show()   
        self.graphview = self.wTree.get_widget("by_category")
        
        kids = self.graphview.get_children()
        if kids:
            self.graphview.remove(kids[0])
        
        self.graphview.pack_start(self.canvas, True, True)








        fig = Figure()

        totals = week["totals"]["by_activity"]
        
        # The numbers here are margins from the edge of the graph
        # You may need to adjust this depending on how you want your
        # graph to look, and how large your labels are
        ax = fig.add_axes([0.5, 0.1, 0.45, 0.8])
        
        i = 0
        labels = {}
        for entry in totals:
            ax.barh(i, totals[entry] / 60, color=color_list[i])
            labels[i] = entry
            i = i + 1


        ax.set_yticks(range(len(totals)+1))
        ax.set_yticklabels(labels, va="bottom")
        

        self.canvas = FigureCanvas(fig) # a gtk.DrawingArea   
        self.canvas.show()   
        self.graphview = self.wTree.get_widget("by_activity")
        
        kids = self.graphview.get_children()
        if kids:
            self.graphview.remove(kids[0])
        
        self.graphview.pack_start(self.canvas, True, True)





        
        
        fig = Figure()

        # The numbers here are margins from the edge of the graph
        # You may need to adjust this depending on how you want your
        # graph to look, and how large your labels are
        ax = fig.add_axes([0.1, 0.1, 0.85, 0.8])
        
        totals = self.get_totals()

        dates = {}
        for total in totals: 
            ax.bar(total["num"], total["hours"], color="#8ae234")
            dates[total['num']] = total['date']
        ax.set_xticklabels(dates, ha = "left")
        

        self.canvas = FigureCanvas(fig) # a gtk.DrawingArea   
        self.canvas.show()   
        self.graphview = self.wTree.get_widget("by_date")
        
        kids = self.graphview.get_children()
        if kids:
            self.graphview.remove(kids[0])
        
        self.graphview.pack_start(self.canvas, True, True)
        
    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.wTree.get_widget(name)

    def on_prev_clicked(self, button):
        self.monday -= dt.timedelta(7)
        self.do_graph()

    def on_next_clicked(self, button):
        self.monday += dt.timedelta(7)
        self.do_graph()
    
    
    def show(self):
        self.window.show_all()

