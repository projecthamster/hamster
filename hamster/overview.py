#!/usr/bin/env python
# - coding: utf-8 -
import pygtk
pygtk.require('2.0')

import os
import gtk
import gtk.glade
from pango import ELLIPSIZE_END

from hamster import dispatcher, storage, SHARED_DATA_DIR
import time
import datetime as dt

GLADE_FILE = "overview.glade"

def format_duration(duration):
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

class DayStore(object):
    """A day view contains a treeview for facts of the day and another
       one for totals. It creates those widgets on init, use
       fill_view(store) to fill the tree and calculate totals """

    def __init__(self, date = None):
        date = date or dt.date.today()
        
        # ID, Time, Name, Duration, Date
        self.fact_store = gtk.ListStore(int, str, str, str, str)
        
        # Dummy ID to distinct between fact_store, Name, Duration
        self.total_store = gtk.ListStore(int, str, str)

        self.facts = storage.get_facts(date)
        self.totals = {}
        
        for fact in self.facts:
            duration = 0
            
            if fact["end_time"]: # not set if just started
                delta = fact["end_time"] - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60
            
            fact_name = fact['name']
            
            if fact_name not in self.totals:
                self.totals[fact_name] = 0

            self.totals[fact_name] += duration

            current_duration = format_duration(duration)

            self.fact_store.append([fact['id'], fact['name'], 
                                    fact["start_time"].strftime("%H:%M"), 
                                    current_duration, fact["start_time"].strftime("%Y%m%d")])

        # now we are good to append totals!
        # no sorting - chronological is intuitive
        for total in self.totals:
            if (self.totals[total]) > 0: # TODO - check if this zero check is still necessary (it was 6min check before) 
                self.total_store.append([-1, format_duration(self.totals[total]), total])


class OverviewController:
    def __init__(self, evBox):
        self.wTree = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, GLADE_FILE))
        self.window = self.get_widget('overview_window')
        self.evBox = evBox

        self.today = dt.datetime.today()
        self.monday = self.today - dt.timedelta(self.today.weekday())
        self.current_view = None
        
        dispatcher.add_handler('activity_updated', self.after_activity_update)
        dispatcher.add_handler('day_updated', self.after_fact_update)

        # now let's set up tree columns!
        # the last widget is total totals
        for i in range(8):
            treeview = self.get_widget('day_' + str(i))
            
            if treeview:
                treeview.set_tooltip_column(1)
                treeview.connect("button-press-event", self.single_focus)
                treeview.connect("key-press-event", self.on_key_pressed)
                
                timeColumn = gtk.TreeViewColumn('Time')
                timeColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
                timeColumn.set_expand(False)
                timeCell = gtk.CellRendererText()
                timeColumn.pack_start(timeCell, True)
                timeColumn.set_attributes(timeCell, text=2)
                treeview.append_column(timeColumn)

                nameColumn = gtk.TreeViewColumn(_(u'Name'))
                nameColumn.set_expand(True)
                nameCell = gtk.CellRendererText()
                nameCell.set_property('ellipsize', ELLIPSIZE_END)
                nameColumn.pack_start(nameCell, True)
                nameColumn.set_attributes(nameCell, text=1)
                treeview.append_column(nameColumn)
                
                durationColumn = gtk.TreeViewColumn(' ')
                durationColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
                durationColumn.set_expand(False)
                durationCell = gtk.CellRendererText()
                durationColumn.pack_start(durationCell, True)
                durationColumn.set_attributes(durationCell, text=3)
                treeview.append_column(durationColumn)

            treeview = self.get_widget('totals_' + str(i))
            treeview.set_tooltip_column(2)
            treeview.connect("button-press-event", self.single_focus)
            nameColumn = gtk.TreeViewColumn(_(u'Name'))
            nameColumn.set_expand(True)
            nameCell = gtk.CellRendererText()
            nameCell.set_property('ellipsize', ELLIPSIZE_END)
            nameColumn.pack_start(nameCell, True)
            nameColumn.set_attributes(nameCell, text=2)
            treeview.append_column(nameColumn)

            timeColumn = gtk.TreeViewColumn(_(u'Time'))
            timeColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            timeColumn.set_expand(False)
            timeCell = gtk.CellRendererText()
            timeColumn.pack_start(timeCell, True)
            timeColumn.set_attributes(timeCell, text=1)
            treeview.append_column(timeColumn)

        self.load_days()
        self.wTree.signal_autoconnect(self)

    def after_activity_update(self, widget, renames):
        if renames:
            self.load_days()
    
    def after_fact_update(self, widget, date):
        for i in range(7):
            current_date = self.monday + dt.timedelta(i)
            if date.date() == current_date.date():
                print "fact updated"
                self.load_days()
                break
    
    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.wTree.get_widget(name)


    def load_days(self):
        self.totals = {}
        self.selected_date = self.monday
        self.total_store = gtk.ListStore(int, str, str)

        for i in range(7):
            current_date = self.monday + dt.timedelta(i)

            label = self.get_widget('label_' + str(i))
            label.set_text('<b>' + current_date.strftime('%A, %b %d.') + '</b>')
            label.set_use_markup(True);

            day = DayStore(current_date);

            treeview = self.get_widget('day_' + str(i))
            treeview.set_model(day.fact_store)

            treeview = self.get_widget('totals_' + str(i))
            treeview.set_model(day.total_store)

            #append totals to week's totals
            for total in day.totals:
                if total not in self.totals:
                    self.totals[total] = 0

                self.totals[total] += day.totals[total]

        for total in self.totals:
            if self.totals[total] >= 0: #TODO - check if this zero check is still necessarry
                self.total_store.append([-1, format_duration(self.totals[total]), total])

        treeview = self.get_widget('totals_7')
        treeview.set_model(self.total_store)

    def single_focus(self, tree, event):
        """ single focus makes sure, that only one window is selected 
            at the same time """
        self.current_view = tree

        for i in range(8):
          treeview = self.get_widget('day_' + str(i))
          if treeview:
              if tree != treeview:
                treeview.get_selection().unselect_all()
              else:
                self.selected_date = self.monday + dt.timedelta(i)
          
          
          treeview = self.get_widget('totals_' + str(i))
          if (tree != treeview):
            treeview.get_selection().unselect_all()

    def show(self):
        self.window.show_all()

    def on_prev_clicked(self, button):
        self.monday -= dt.timedelta(7)
        self.load_days()

    def on_next_clicked(self, button):
        self.monday += dt.timedelta(7)
        self.load_days()
    
    def on_key_pressed(self, tree, event_key):
      if (event_key.keyval == gtk.keysyms.Delete):
        self.delete_selected()
      elif (event_key.keyval == gtk.keysyms.Insert):
        self.on_add_clicked(self)

    def on_remove_clicked(self, button):
        self.delete_selected()

    def on_add_clicked(self, button):
        from hamster.add_custom_fact import CustomFactController
        #date = selected_date.strftime('%Y%m%d')

        custom_fact = CustomFactController(self.evBox, self.selected_date)
        custom_fact.show()

    def delete_selected(self):
        view = self.current_view
        if not view: return  
      
        selection = view.get_selection()
        (model, iter) = selection.get_selected()

        next_row = model.iter_next(iter)

        if next_row:
            selection.select_iter(next_row)
        else:
            path = model.get_path(iter)[0] - 1
            if path > 0:
                selection.select_path(path)


        storage.remove_fact(model[iter][0])
        self.evBox.fact_updated(model[iter][4])
        model.remove(iter)
    
    def on_home_clicked(self, button):
        self.today = dt.date.today() #midnight check, huh
        self.monday = self.today - dt.timedelta(self.today.weekday())
        self.load_days()

if __name__ == '__main__':
    controller = OverviewController()
    controller.show()
    gtk.main()


