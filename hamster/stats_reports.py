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
import gtk, gobject
import pango

import stuff
import charting

from edit_activity import CustomFactController
import reports, graphics

import widgets

from configuration import runtime, GconfStore
import webbrowser

from itertools import groupby
from gettext import ngettext

import datetime as dt
import calendar
import time
from hamster.i18n import C_


class ReportsBox(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)
        self._gui = stuff.load_ui_file("stats_reports.ui")
        self.get_widget("reports_box").reparent(self) #mine!

        self.view_date = dt.date.today()
        
        #set to monday
        self.start_date = self.view_date - \
                                      dt.timedelta(self.view_date.weekday() + 1)
        # look if we need to start on sunday or monday
        self.start_date = self.start_date + \
                                      dt.timedelta(stuff.locale_first_weekday())
        
        self.end_date = self.start_date + dt.timedelta(6)

        
        self.totals_tree = TotalsTree()
        self.get_widget("totals_tree_box").add(self.totals_tree)
        
        
        #graphs
        self.background = (0.975, 0.975, 0.975)
        self.get_widget("graph_frame").modify_bg(gtk.STATE_NORMAL,
                      gtk.gdk.Color(*[int(b*65536.0) for b in self.background]))


        x_offset = 90 # align all graphs to the left edge
        
        self.category_chart = charting.BarChart(background = self.background,
                                             bar_base_color = (238,221,221),
                                             legend_width = x_offset,
                                             max_bar_width = 35,
                                             show_stack_labels = True
                                             )
        self.get_widget("totals_by_category").add(self.category_chart)
        

        self.day_chart = charting.BarChart(background = self.background,
                                           bar_base_color = (220, 220, 220),
                                           show_scale = True,
                                           max_bar_width = 35,
                                           grid_stride = 4,
                                           legend_width = 20)
        self.get_widget("totals_by_day").add(self.day_chart)


        self.activity_chart = charting.HorizontalBarChart(orient = "horizontal",
                                                   max_bar_width = 25,
                                                   values_on_bars = True,
                                                   stretch_grid = True,
                                                   legend_width = x_offset,
                                                   value_format = "%.1f",
                                                   background = self.background,
                                                   bars_beveled = False,
                                                   animate = False)
        self.get_widget("totals_by_activity").add(self.activity_chart);

        
        runtime.dispatcher.add_handler('activity_updated', self.after_activity_update)
        runtime.dispatcher.add_handler('day_updated', self.after_fact_update)


        self.popular_categories = [cat[0] for cat in runtime.storage.get_popular_categories()]

        self._gui.connect_signals(self)
        self.totals_tree.grab_focus()

        
        self.config = GconfStore()
        runtime.dispatcher.add_handler('gconf_on_day_start_changed', self.on_day_start_changed)

        self.report_chooser = None
        #self.fill_totals_tree()
        #self.do_graph()


    def search(self, start_date, end_date, facts):
        self.start_date = start_date
        self.end_date = end_date
        self.fill_totals_tree(facts)
        self.do_graph(facts)



    def fill_totals_tree(self, facts = None):        
        facts = facts or runtime.storage.get_facts(self.start_date, self.end_date)


        #first group by category, activity and tags
        #sort before grouping
        facts = sorted(facts, key = lambda fact:(fact["category"], fact["name"], fact["tags"]))

        totals = []
        for group, facts in groupby(facts, lambda fact:(fact["category"], fact["name"], fact["tags"])):
            facts = list(facts)
            total_duration = dt.timedelta()
            for fact in facts:
                total_duration += fact["delta"]
            
            group = list(group)
            group.extend([total_duration, len(facts)])
            totals.append(group)

        self.totals_tree.clear()
        
        # second iteration - group the interim result by category
        i = 0
        for category, totals in groupby(totals, lambda total:total[0]):
            i+=1
            totals = list(totals)


            category_duration = sum([stuff.duration_minutes(total[3]) for total in totals])
            category_occurences = sum([total[4] for total in totals])
    
            
            # adds group of facts with the given label
            category_row = self.totals_tree.model.append(None,
                                                         [category,
                                                          None,
                                                          stuff.format_duration(category_duration),
                                                          str(category_occurences)])

            #now group by activity too
            for group, totals in groupby(totals, lambda total:(total[0], total[1])):
                totals = list(totals)
    
                if len(totals) > 1:
                    activity_duration = sum([stuff.duration_minutes(total[3]) for total in totals])
                    activity_occurences = sum([total[4] for total in totals])
                    
            
                    # adds group of facts with the given label
                    activity_row = self.totals_tree.model.append(category_row,
                                                                 [group[1],
                                                                  None,
                                                                  stuff.format_duration(activity_duration),
                                                                  str(activity_occurences)])
                    
                    for total in totals:
                        self.totals_tree.add_total(total, activity_row)
                else:
                    self.totals_tree.add_total(totals[0], category_row)
            
            self.totals_tree.expand_row((i-1,), False)


    def on_graph_frame_size_allocate(self, widget, new_size):
        w = min(new_size.width / 4, 200)
        
        self.activity_chart.legend_width = w
        self.category_chart.legend_width = w
        self.get_widget("totals_by_category").set_size_request(w + 40, -1)
    

    def do_charts(self, facts):
        all_categories = self.popular_categories
        
        
        #the single "totals" (by category) bar
        category_sums = stuff.totals(facts, lambda fact: fact["category"],
                      lambda fact: stuff.duration_minutes(fact["delta"]) / 60.0)
        category_totals = [category_sums.get(cat, 0) for cat in all_categories]
        category_keys = ["%s %.1f" % (cat, category_sums.get(cat, 0.0))
                                                      for cat in all_categories]
        self.category_chart.plot([_("Total")],
                                 [category_totals],
                                 stack_keys = category_keys)
        
        # day / category chart
        all_days = [self.start_date + dt.timedelta(i)
                    for i in range((self.end_date - self.start_date).days  + 1)]
        
        by_date_cat = stuff.totals(facts,
                                   lambda fact: (fact["date"], fact["category"]),
                                   lambda fact: stuff.duration_minutes(fact["delta"]) / 60.0)

        res = [[by_date_cat.get((day, cat), 0)
                                 for cat in all_categories] for day in all_days]


        #show days or dates depending on scale
        if (self.end_date - self.start_date).days < 20:
            day_keys = [day.strftime("%a") for day in all_days]
        else:
            # date format used in the overview graph when month view is selected
            # Using python datetime formatting syntax. See:
            # http://docs.python.org/library/time.html#time.strftime
            day_keys = [day.strftime(C_("overview graph", "%b %d"))
                                                            for day in all_days]

        self.day_chart.plot(day_keys, res, stack_keys = all_categories)


        #totals by activity, disguised under a stacked bar chart to get category colors
        activity_sums = stuff.totals(facts,
                                     lambda fact: (fact["name"],
                                                   fact["category"]),
                                     lambda fact: stuff.duration_minutes(fact["delta"]))
        
        #now join activities with same name
        activities = {}
        for key in activity_sums.keys():
            activities.setdefault(key[0], [0.0] * len(all_categories))
            activities[key[0]][all_categories.index(key[1])] = activity_sums[key] / 60.0
            
        by_duration = sorted(activities.items(),
                             key = lambda x: sum(x[1]),
                             reverse = True)
        by_duration_keys = [entry[0] for entry in by_duration]
        
        by_duration = [entry[1] for entry in by_duration]

        self.activity_chart.plot(by_duration_keys,
                                 by_duration,
                                 stack_keys = all_categories)
        
    def do_graph(self, facts = None):
        facts = facts or runtime.storage.get_facts(self.start_date, self.end_date)

        self.get_widget("report_button").set_sensitive(len(facts) > 0)

        self.fill_totals_tree(facts)

        if not facts:
            self.get_widget("graphs").hide()
            self.get_widget("no_data_label").show()
            return 


        self.get_widget("no_data_label").hide()
        self.get_widget("graphs").show()
        self.do_charts(facts)
            

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)




    def after_activity_update(self, widget, renames):
        self.do_graph()
    
    def after_fact_update(self, event, date):
        self.popular_categories = [cat[0] for cat in runtime.storage.get_popular_categories()]
        self.do_graph()


    def init_report_dialog(self):
        chooser = self.get_widget('save_report_dialog')
        chooser.set_action(gtk.FILE_CHOOSER_ACTION_SAVE)
        """
        chooser.set
        
        chooser = gtk.FileChooserDialog(title = _("Save report - Time Tracker"),
                                        parent = None,
                                        buttons=(gtk.STOCK_CANCEL,
                                                 gtk.RESPONSE_CANCEL,
                                                 gtk.STOCK_SAVE,
                                                 gtk.RESPONSE_OK))
        """
        chooser.set_current_folder(os.path.expanduser("~"))

        filters = {}

        filter = gtk.FileFilter()
        filter.set_name(_("HTML Report"))
        filter.add_mime_type("text/html")
        filter.add_pattern("*.html")
        filter.add_pattern("*.htm")
        filters[filter] = "html"
        chooser.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("Tab-Separated Values (TSV)"))
        filter.add_mime_type("text/plain")
        filter.add_pattern("*.tsv")
        filter.add_pattern("*.txt")
        filters[filter] = "tsv"
        chooser.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("XML"))
        filter.add_mime_type("text/xml")
        filter.add_pattern("*.xml")
        filters[filter] = "xml"
        chooser.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("iCal"))
        filter.add_mime_type("text/calendar")
        filter.add_pattern("*.ics")
        filters[filter] = "ical"
        chooser.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        chooser.add_filter(filter)
        
    def on_report_chosen(self, widget, format, path, start_date, end_date,
                                                                    categories):
        self.report_chooser = None
        
        facts = runtime.storage.get_facts(start_date, end_date, category_id = categories)
        reports.simple(facts,
                       start_date,
                       end_date,
                       format,
                       path)

        if format == ("html"):
            webbrowser.open_new("file://%s" % path)
        else:
            gtk.show_uri(gtk.gdk.Screen(),
                         "file://%s" % os.path.split(path)[0], 0L)

    def on_report_chooser_closed(self, widget):
        self.report_chooser = None
        
    def on_report_button_clicked(self, widget):
        if not self.report_chooser:
            self.report_chooser = widgets.ReportChooserDialog()
            self.report_chooser.connect("report-chosen", self.on_report_chosen)
            self.report_chooser.connect("report-chooser-closed",
                                        self.on_report_chooser_closed)
            self.report_chooser.show(self.start_date, self.end_date)
        else:
            self.report_chooser.present()
        
        
    def on_day_start_changed(self, event, new_minutes):
        self.do_graph()



def parent_painter(column, cell, model, iter):
    count = int(model.get_value(iter, 3))
    
    if count > 1:
        cell_text = "%s (&#215;%s)" % (stuff.escape_pango(model.get_value(iter, 0)), count)
    else:
        cell_text = "%s" % stuff.escape_pango(model.get_value(iter, 0))
        
    
    if model.iter_parent(iter) is None:
        if model.get_path(iter) == (0,):
            text = '<span weight="heavy">%s</span>' % cell_text
        else:
            text = '<span weight="heavy" rise="-20000">%s</span>' % cell_text
            
        cell.set_property('markup', text)

    else:
        cell.set_property('markup', cell_text)

def duration_painter(column, cell, model, iter):
    cell.set_property('xalign', 1)


    text = model.get_value(iter, 2)
    if model.iter_parent(iter) is None:
        if model.get_path(iter) == (0,):
            text = '<span weight="heavy">%s</span>' % text
        else:
            text = '<span weight="heavy" rise="-20000">%s</span>' % text
    cell.set_property('markup', text)

class TotalsTree(gtk.TreeView):
    def __init__(self):
        gtk.TreeView.__init__(self)
        
        self.set_headers_visible(False)
        self.set_show_expanders(True)

        # group name / activity name, tags, duration, occurences
        self.set_model(gtk.TreeStore(str, gobject.TYPE_PYOBJECT, str, str))
        
        # name
        nameColumn = gtk.TreeViewColumn()
        nameCell = gtk.CellRendererText()
        #nameCell.set_property("ellipsize", pango.ELLIPSIZE_END)
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_cell_data_func(nameCell, parent_painter)
        self.append_column(nameColumn)

        tag_cell = widgets.TagCellRenderer()
        tag_cell.set_font_size(8);
        tagColumn = gtk.TreeViewColumn("", tag_cell, data=1)
        tagColumn.set_expand(True)

        self.append_column(tagColumn)

        # duration
        timeColumn = gtk.TreeViewColumn()
        timeCell = gtk.CellRendererText()
        timeColumn.pack_end(timeCell, True)
        timeColumn.set_cell_data_func(timeCell, duration_painter)
        self.append_column(timeColumn)


        self.show()
    
    def clear(self):
        self.model.clear()
        
    @property
    def model(self):
        return self.get_model()
        
    def add_total(self, total, parent = None):
        duration = stuff.duration_minutes(total[3])


        self.model.append(parent, [total[1],
                                   total[2],
                                   stuff.format_duration(duration),
                                   str(total[4])])

    def add_group(self, group_label, totals):
        total_duration = sum([stuff.duration_minutes(total[3]) for total in totals])
        total_occurences = sum([total[4] for total in totals])

        
        # adds group of facts with the given label
        group_row = self.model.append(None,
                                    [group_label,
                                     None,
                                     stuff.format_duration(total_duration),
                                     str(total_occurences)])
        
        for total in totals:
            self.add_total(total, group_row)

        self.expand_all()


        



if __name__ == "__main__":
    gtk.window_set_default_icon_name("hamster-applet")    
    window = gtk.Window()
    window.set_title("Hamster - reports")
    window.set_size_request(800, 600)
    window.add(ReportsBox())

    window.show_all()    
    gtk.main()    

