#!/usr/bin/env python
import pygtk
pygtk.require('2.0')

import os
import gtk
import gtk.glade

import hamster
import hamster.db
import time
import datetime as dt

GLADE_FILE = "overview.glade"

class DayStore(object):
    """A day view contains a treeview for facts of the day and another
       one for totals. It creates those widgets on init, user
       fill_view(store) to fill the tree and calculate totals """

    def __init__(self, date = time.strftime('%Y%m%d')):
        self.fact_store = gtk.ListStore(int, str, str)
        self.total_store = gtk.ListStore(int, str, str)

        db_facts = hamster.db.get_facts(date)

        prev_fact, prev_time = None, None
        self.totals = {}

        for fact in db_facts:
            hours = fact['fact_time'][:2]
            minutes = fact['fact_time'][2:4]
            self.fact_store.append([fact['id'], fact['name'], hours + ':' + minutes])

            # we need time only for delta, so let's convert to mins
            fact_time = int(hours) * 60 + int(minutes)

            if prev_fact:
                duration = fact_time - prev_time
                if not self.totals.has_key(prev_fact):
                    self.totals[prev_fact] = 0

                self.totals[prev_fact] += duration

            prev_fact, prev_time = fact['name'], fact_time

        # now we are good to append totals!
        # no sorting - chronological is intuitive
        for total in self.totals:
            if (self.totals[total] / 60.0) >= 0.1:
                in_hours = self.totals[total] / 60.0
                self.total_store.append([-1, "%.1fh" % in_hours, total])


class OverviewController:
    def __init__(self):
        self.wTree = gtk.glade.XML(os.path.join(hamster.SHARED_DATA_DIR, GLADE_FILE))
        self.window = self.get_widget('overview_window')

        self.today = dt.datetime.today()
        self.monday = self.today - dt.timedelta(self.today.weekday())
        self.current_view = None

        # now let's set up tree columns!
        # the last widget is total totals
        for i in range(8):
            treeview = self.get_widget('day_' + str(i))
            
            if treeview:
                treeview.connect("button-press-event", self.single_focus)
                treeview.connect("key-press-event", self.on_key_pressed)
                
                timeColumn = gtk.TreeViewColumn('Time')
                timeColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
                timeColumn.set_expand(False)
                timeCell = gtk.CellRendererText()
                timeColumn.pack_start(timeCell, True)
                timeColumn.set_attributes(timeCell, text=2)
                treeview.append_column(timeColumn)

                nameColumn = gtk.TreeViewColumn('Name')
                nameColumn.set_expand(True)
                nameCell = gtk.CellRendererText()
                nameColumn.pack_start(nameCell, True)
                nameColumn.set_attributes(nameCell, text=1)
                treeview.append_column(nameColumn)

            treeview = self.get_widget('totals_' + str(i))
            treeview.connect("button-press-event", self.single_focus)
            nameColumn = gtk.TreeViewColumn('Name')
            nameColumn.set_expand(True)
            nameCell = gtk.CellRendererText()
            nameColumn.pack_start(nameCell, True)
            nameColumn.set_attributes(nameCell, text=2)
            treeview.append_column(nameColumn)

            timeColumn = gtk.TreeViewColumn('Time')
            timeColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            timeColumn.set_expand(False)
            timeCell = gtk.CellRendererText()
            timeColumn.pack_start(timeCell, True)
            timeColumn.set_attributes(timeCell, text=1)
            treeview.append_column(timeColumn)


        self.load_days()
        self.wTree.signal_autoconnect(self)

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self.wTree.get_widget(name)


    def load_days(self):
        self.totals = {}
        self.total_store = gtk.ListStore(int, str, str)

        for i in range(7):
            current_date = self.monday + dt.timedelta(i)

            label = self.get_widget('label_' + str(i))
            label.set_text('<b>' + current_date.strftime('%A, %b %d.') + '</b>')
            label.set_use_markup(True);

            day = DayStore(current_date.strftime('%Y%m%d'));

            treeview = self.get_widget('day_' + str(i))
            treeview.set_model(day.fact_store)

            treeview = self.get_widget('totals_' + str(i))
            treeview.set_model(day.total_store)

            #append totals to week's totals
            for total in day.totals:
                if not self.totals.has_key(total):
                    self.totals[total] = 0

                self.totals[total] += day.totals[total]

        for total in self.totals:
            if (self.totals[total] / 60.0) >= 0.1:
                in_hours = self.totals[total] / 60.0
                self.total_store.append([-1, "%.1fh" % in_hours, total])

        treeview = self.get_widget('totals_7')
        treeview.set_model(self.total_store)

    def single_focus(self, tree, event):
        """ single focus makes sure, that only one window is selected 
            at the same time """
        self.current_view = tree

        for i in range(8):
          treeview = self.get_widget('day_' + str(i))
          
          if (treeview and tree != treeview):
            treeview.get_selection().unselect_all()
          
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

    def on_remove_clicked(self, button):
        self.delete_selected()

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


        hamster.db.remove_fact(model[iter][0])
        model.remove(iter)
    
    def on_home_clicked(self, button):
        self.today = dt.datetime.today() #midnight check, huh
        self.monday = self.today - dt.timedelta(self.today.weekday())
        self.load_days()

if __name__ == '__main__':
    controller = OverviewController()
    controller.show()
    gtk.main()


