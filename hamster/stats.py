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

import math

#some hand-picked tango colors
color_list = [
    "#edd400", "#f57900", "#c17d11", "#73d216", "#3465a4", "#75507b", "#cc0000",
    "#fcaf3e", "#e9b96e", "#8ae234", "#729fcf", "#ad7fa8", "#ef2929",
    "#c4a000", "#ce5c00", "#8f5902", "#4e9a06", "#204a87", "#5c3566", "a40000"
]

# Tango colors
light = [(252, 233, 79),  (138, 226, 52),  (252, 175, 62),
         (114, 159, 207), (173, 127, 168), (233, 185, 110),
         (239, 41,  41),  (238, 238, 236), (136, 138, 133)]

medium = [(237, 212, 0),   (115, 210, 22),  (245, 121, 0),
          (52,  101, 164), (117, 80,  123), (193, 125, 17),
          (204, 0,   0),   (211, 215, 207), (85, 87, 83)]

dark = [(196, 160, 0), (78, 154, 6), (206, 92, 0),
        (32, 74, 135), (92, 53, 102), (143, 89, 2),
        (164, 0, 0), (186, 189, 182), (46, 52, 54)]


def set_color(context, color):
    r,g,b = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
    context.set_source_rgb(r, g, b)
    
    
class Chart(gtk.DrawingArea):
    def __init__(self, vertical = True):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.data = None #start off with an empty hand
        
        self.max_size = 100 # maximal size of bar
        
        self.step = 35 # distance between one and the next bar
        self.bar_width = 30 #bar width
        
        self.offset_x = 50 # graph offset in pixels inside canvas
        self.offset_y = 50 # graph offset in pixels inside canvas
        
    def expose(self, widget, event): # expose is when drawing's going on
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        context.clip()
        
        self.draw(context)
        return False

    def plot(self, data):
        self.data = data

        if self.window:    #this can get called before expose    
            alloc = self.get_allocation()
            rect = gtk.gdk.Rectangle(alloc.x, alloc.y, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)
        
    
    def draw(self, context):
        rect = self.get_allocation()  #x, y, width, height        

        graph_x = rect.x + self.offset_x
        graph_y = rect.y + self.offset_y


        context.set_line_width(1)
        
        data = self.data
        
        #find max, so we know
        max = 0.1
        for i in data:
            if i[1] > max: max = i[1] * 1.0
        

        # TODO put this somewhere else - drawing background and some grid
        context.rectangle(graph_x - 1, rect.y, self.step * len(data), 101)
        context.set_source_rgb(1, 1, 1)
        context.fill_preserve()

        context.set_line_width(1)
        context.set_dash ([1, 3]);

        set_color(context, dark[8])
        
        for y in range(rect.y, rect.y + self.max_size + 5, self.max_size / 3):
            context.move_to(graph_x - 10, y)
            context.line_to(graph_x + self.step * len(data), y)

        context.stroke()
        
        
        context.set_dash ([]);
        # bars themselves
        for i in range(len(data)):
            context.rectangle(graph_x + (self.step * i),
                              rect.y + self.max_size - (self.max_size * (data[i][1] / max)),
                              self.bar_width,
                              (self.max_size * (data[i][1] / max)))

        set_color(context, light[1])
        context.fill_preserve()

        set_color(context, dark[1]);
        context.stroke()
        
        # labels
        set_color(context, dark[8]);
        for i in range(len(data)):
            context.move_to(graph_x + 5 + (self.step * i), rect.y + self.max_size + 15)
            context.show_text(data[i][0])

        # values for max minn and average
        context.move_to(rect.x + 10, rect.y + 10)
        context.show_text(str(max))

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

        self.day_chart = Chart()
        eventBox = gtk.EventBox()
        place = self.get_widget("cairo_by_week")
        eventBox.add(self.day_chart);
        place.add(eventBox)
        
        
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
        
        totals['by_day'] = []
        totals['by_activity'] = {}
        totals['by_category'] = {}
        
        week = {"days": [], "totals": []}
            
        for i in range(7):
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
                    
                    if fact["name"] not in totals['by_activity']: totals['by_activity'][fact["name"]] = 0
                    if fact["category"] not in totals['by_category']: totals['by_category'][fact["category"]] = 0

                    totals['by_activity'][fact["name"]] += duration
                    totals['by_category'][fact["category"]] += duration
                    day_total += duration

            totals['by_day'].append((current_date.strftime('%a'), day_total / 60))
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

        self.day_chart.plot(week["totals"]["by_day"])

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

