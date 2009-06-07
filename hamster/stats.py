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
import gtk
import pango

from hamster import dispatcher, storage, SHARED_DATA_DIR, stuff
from hamster import charting

from hamster.edit_activity import CustomFactController
import webbrowser

import datetime as dt
import calendar
import time

class StatsViewer(object):
    def __init__(self, parent = None):
        self.parent = parent# determine if app shut shut down on close
        self._gui = stuff.load_ui_file("stats.ui")
        self.window = self.get_widget('stats_window')

        #id, caption, duration, date (invisible), description, category
        self.fact_store = gtk.TreeStore(int, str, str, str, str, str) 
        self.setup_tree()
        
        graph_frame = self.get_widget("graph_frame")
        background = (0.975,0.975,0.975)
        graph_frame.modify_bg(gtk.STATE_NORMAL,
                              gtk.gdk.Color(*[int(b*65536.0) for b in background]))

        
        x_offset = 90 # let's nicely align all graphs
        
        self.category_chart = charting.BarChart(background = background,
                                             bar_base_color = (238,221,221),
                                             bars_beveled = False,
                                             legend_width = x_offset,
                                             max_bar_width = 35,
                                             show_stack_labels = True
                                             )
        category_box = self.get_widget("totals_by_category")
        category_box.add(self.category_chart)
        category_box.set_size_request(130, -1)
        

        self.day_chart = charting.BarChart(background = background,
                                        bar_base_color = (220, 220, 220),
                                        bars_beveled = False,
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
                                             background = background,
                                             bars_beveled = False,
                                             animate = False)
        self.get_widget("totals_by_activity").add(self.activity_chart);

        
        self.view_date = dt.date.today()
        
         #set to monday
        self.start_date = self.view_date - \
                                      dt.timedelta(self.view_date.weekday() + 1)
        # look if we need to start on sunday or monday
        self.start_date = self.start_date + \
                                      dt.timedelta(self.locale_first_weekday())
        
        self.end_date = self.start_date + dt.timedelta(6)

        
        self.week_view = self.get_widget("week")
        self.month_view = self.get_widget("month")
        self.month_view.set_group(self.week_view)
        
        #initiate the form in the week view
        self.week_view.set_active(True)


        dispatcher.add_handler('activity_updated', self.after_activity_update)
        dispatcher.add_handler('day_updated', self.after_fact_update)

        selection = self.fact_tree.get_selection()
        selection.connect('changed', self.on_fact_selection_changed,
                          self.fact_store)
        self.popular_categories = [cat[0] for cat in storage.get_popular_categories()]

        self._gui.connect_signals(self)
        self.fact_tree.grab_focus()
        
        """
        # this will help when profiling!
        import gobject
        self.i = 0
        def redraw():
            self.do_graph()
            self.start_date -= dt.timedelta(7)
            self.end_date -= dt.timedelta(7)
            self.i +=1
            return self.i < 50
            
        gobject.timeout_add(400, redraw)
        """
        self.do_graph()

    def more_on_left(self):
        z = min(round((self.end_date - self.start_date).days / 21.0)+1, 5)
        self.start_date = self.start_date - dt.timedelta(days = z)
        self.do_graph()
        
    def less_on_left(self):
        z = min(round((self.end_date - self.start_date).days / 21.0)+1, 5)
        self.start_date = self.start_date + dt.timedelta(days=z)
        self.do_graph()
        
    def setup_tree(self):
        def parent_painter(column, cell, model, iter):
            cell_text = model.get_value(iter, 1)
            if model.iter_parent(iter) is None:
                if model.get_path(iter) == (0,):
                    text = '<span weight="heavy">%s</span>' % cell_text
                else:
                    text = '<span weight="heavy" rise="-20000">%s</span>' % cell_text
                    
                cell.set_property('markup', text)
    
            else:
                activity_name = stuff.escape_pango(cell_text)
                description = stuff.escape_pango(model.get_value(iter, 4))
                category = stuff.escape_pango(model.get_value(iter, 5))

                markup = stuff.format_activity(activity_name, category, description, pad_description = True)            
                cell.set_property('markup', markup)

        def duration_painter(column, cell, model, iter):
            cell.set_property('xalign', 1)
            cell.set_property('yalign', 0)
    

            text = model.get_value(iter, 2)
            if model.iter_parent(iter) is None:
                if model.get_path(iter) == (0,):
                    text = '<span weight="heavy">%s</span>' % text
                else:
                    text = '<span weight="heavy" rise="-20000">%s</span>' % text
            cell.set_property('markup', text)
    

        self.fact_tree = self.get_widget("facts")
        self.fact_tree.set_headers_visible(False)
        self.fact_tree.set_tooltip_column(1)
        self.fact_tree.set_property("show-expanders", False)

        # name
        nameColumn = gtk.TreeViewColumn()
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()
        nameCell.set_property("ellipsize", pango.ELLIPSIZE_END)
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_cell_data_func(nameCell, parent_painter)
        self.fact_tree.append_column(nameColumn)

        # duration
        timeColumn = gtk.TreeViewColumn()
        timeCell = gtk.CellRendererText()
        timeColumn.pack_end(timeCell, True)
        timeColumn.set_cell_data_func(timeCell, duration_painter)




        self.fact_tree.append_column(timeColumn)
        
        self.fact_tree.set_model(self.fact_store)
        
        
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
        
    def get_facts(self, facts):
        self.fact_store.clear()
        totals = {}

        by_activity = {}
        by_category = {}
        by_day = {}

        for i in range((self.end_date - self.start_date).days  + 1):
            current_date = self.start_date + dt.timedelta(i)
            # date format in overview window fact listing
            # prefix is "o_",letter after prefix is regular python format. you can use all of them
            fact_date = _("%(o_A)s, %(o_b)s %(o_d)s") %  stuff.dateDict(current_date, "o_")

            day_row = self.fact_store.append(None, [-1,
                                                    fact_date,
                                                    "",
                                                    current_date.strftime('%Y-%m-%d'),
                                                    "", ""])
            by_day[self.start_date + dt.timedelta(i)] = {"duration": 0, "row_pointer": day_row}

                
                

        for fact in facts:
            start_date = fact["date"]

            duration = None
            if fact["delta"]:
                duration = 24 * fact["delta"].days + fact["delta"].seconds / 60

            self.fact_store.append(by_day[start_date]["row_pointer"],
                                   [fact["id"],
                                    fact["start_time"].strftime('%H:%M') + " " +
                                    fact["name"],
                                    stuff.format_duration(duration),
                                    fact["start_time"].strftime('%Y-%m-%d'),
                                    fact["description"],
                                    fact["category"]
                                    ])

            if duration:
                by_day[start_date]["duration"] += duration


        for day in by_day:
            self.fact_store.set_value(by_day[day]["row_pointer"], 2,
                stuff.format_duration(by_day[day]["duration"]))


        self.fact_tree.expand_all()
        
        self.get_widget("report_button").set_sensitive(len(facts) > 0)


        
    def get_totals(self, facts, all_days):
        # get list of used activities in interval
        activities = [act[0] for act in
              storage.get_interval_activity_ids(self.start_date, self.end_date)]

        # fill in the activity totals blanks
        # don't want to add ability to be able to specify color per bar
        # so we will be disguising our bar chart as multibar chart
        activity_totals = {}
        for act in activities:
            activity_totals[act] = {}
            for cat in self.popular_categories:
                activity_totals[act][cat] = 0

        # fill in the category totals blanks
        day_category_totals = {}
        for day in all_days:
            day_category_totals[day] = {}
            for cat in self.popular_categories:
                day_category_totals[day][cat] = 0
            
        #now we do the counting
        for fact in facts:
            duration = None
            start_date = fact['date']
            
            if fact["end_time"]: # not set if just started
                delta = fact["end_time"] - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60
            elif start_date == dt.date.today():
                delta = dt.datetime.now() - fact["start_time"]
                duration = 24 * delta.days + delta.seconds / 60

            activity_totals[fact['name']][fact['category']] += duration or 0
            day_category_totals[start_date][fact['category']] += duration or 0


        # convert dictionaries into lists so we don't have to care about keys anymore
        res_categories = []
        for day in all_days:
            res_categories.append([day_category_totals[day][cat] / 60.0
                                            for cat in self.popular_categories])
            
        #sort activities by duration, longest first
        activity_totals = activity_totals.items()
        activity_totals = sorted(activity_totals,
                                 key = lambda(k,v): (max(v.values()), k),
                                 reverse = True)
        
        activities = [] #we have changed the order
        res_activities = []
        for act in activity_totals:
            activities.append(act[0])
            res_activities.append([act[1][cat] / 60.0
                                            for cat in self.popular_categories])

        return {'keys': activities, 'values': res_activities}, \
               {'keys': self.popular_categories, 'values': res_categories}
        

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

        if self.week_view.get_active():
            dayview_caption = _("Week")
        else:
            dayview_caption = _("Month")
        
        
        label = self.get_widget("overview_label")
        label.set_text(overview_label)

        label2 = self.get_widget("dayview_caption")
        label2.set_markup("%s" % (dayview_caption))
        
        fact_list = storage.get_facts(self.start_date, self.end_date)

        self.get_facts(fact_list)
        
        if not fact_list:
            self.get_widget("graphs").hide()
            self.get_widget("no_data_label").show()
            return 
        else:
            self.get_widget("graphs").show()
            self.get_widget("no_data_label").hide()
            

        all_days = [self.start_date + dt.timedelta(i)
                    for i in range((self.end_date - self.start_date).days  + 1)]        

        activity_totals, day_category_totals = self.get_totals(fact_list, all_days)

        
        
        self.activity_chart.plot(activity_totals['keys'],
                                  activity_totals['values'],
                                  stack_keys = self.popular_categories)


        #show days or dates depending on scale
        if (self.end_date - self.start_date).days < 20:
            day_keys = [day.strftime("%a") for day in all_days]
        else:
            day_keys = [_("%(m_b)s %(m_d)s") %  stuff.dateDict(day, "m_") for day in all_days]


        self.day_chart.plot(day_keys, day_category_totals['values'],
                             stack_keys = day_category_totals['keys'])

        category_totals = [[sum(value) for value in zip(*day_category_totals['values'])]]
        
        category_keys = []
        for i in range(len(day_category_totals['keys'])):
            category_keys.append("%s %.1f" % (day_category_totals['keys'][i], category_totals[0][i]))
        

        self.category_chart.plot([_("Total")], category_totals,
                                  stack_keys = category_keys)


    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def on_prev_clicked(self, button):
        if self.week_view.get_active():
            self.start_date -= dt.timedelta(7)
            self.end_date -= dt.timedelta(7)
        
        elif self.month_view.get_active():
            self.end_date = self.start_date - dt.timedelta(1)
            first_weekday, days_in_month = calendar.monthrange(self.end_date.year, self.end_date.month)
            self.start_date = self.end_date - dt.timedelta(days_in_month - 1)

        self.view_date = self.start_date        
        self.do_graph()

    def on_next_clicked(self, button):
        if self.week_view.get_active():
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
        if self.week_view.get_active():
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

        custom_fact = CustomFactController(self, None, model[iter][0])
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
        custom_fact = CustomFactController(self, None, model[iter][0])
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

        custom_fact = CustomFactController(self, selected_date)
        custom_fact.show()
        
    def on_report_button_clicked(self, widget):
        chooser = gtk.FileChooserDialog(title = _("Save report - Time Tracker"),
                                        parent = None,
                                        action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                        buttons=(gtk.STOCK_CANCEL,
                                                 gtk.RESPONSE_CANCEL,
                                                 gtk.STOCK_SAVE,
                                                 gtk.RESPONSE_OK))

        chooser.set_current_folder(os.path.expanduser("~"))

        #set suggested name to something readable, replace backslashes with dots
        #so the name is valid in linux
        filename = "Time track %s - %s" % (self.start_date.strftime("%x").replace("/", "."),
                                           self.end_date.strftime("%x").replace("/", "."))
        chooser.set_current_name(filename)

        filters = {}

        filter = gtk.FileFilter()
        filter.set_name(_("HTML Report"))
        filter.add_mime_type("text/html")
        filter.add_pattern("*.html")
        filter.add_pattern("*.htm")
        filters[filter] = "html"
        chooser.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("Tab Separated Values (TSV)"))
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
        
        
        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            format = "html"
            if chooser.get_filter() in filters:
                format = filters[chooser.get_filter()]

            from hamster import reports
            facts = storage.get_facts(self.start_date, self.end_date)
            path = chooser.get_filename()
            
            reports.simple(facts,
                           self.start_date,
                           self.end_date,
                           format,
                           path)

            if format == ("html"):
                webbrowser.open_new("file://%s" % path)
            else:
                gtk.show_uri(gtk.gdk.Screen(),
                             "file://%s" % os.path.split(path)[0], 0L)

        chooser.destroy()
        
        # supported types: HTML, CSV, XML
        #save_as.add
        
        

    def after_activity_update(self, widget, renames):
        self.do_graph()
    
    def after_fact_update(self, event, date):
        self.popular_categories = [cat[0] for cat in storage.get_popular_categories()]
        self.do_graph()
        
    def on_close(self, widget, event):
        dispatcher.del_handler('activity_updated', self.after_activity_update)
        dispatcher.del_handler('day_updated', self.after_fact_update)
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

