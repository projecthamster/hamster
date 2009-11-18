#!/usr/bin/env python
# - coding: utf-8 -

# Copyright (C) 2009 Toms Bauģis <toms.baugis at gmail.com>

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

import logging
import datetime as dt

import pygtk
pygtk.require("2.0")
import gtk
#gtk.gdk.threads_init()

from configuration import GconfStore, runtime
import stuff, widgets

import gobject

class ActivityEntry(gtk.Entry):
    __gsignals__ = {
        'value-entered': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }


    def __init__(self):
        gtk.Entry.__init__(self)
        self.news = False
        self.activities = None
        self.categories = None
        self.filter = None
        self.max_results = 10 # limit popup size to 10 results
        
        self.popup = gtk.Window(type = gtk.WINDOW_POPUP)
        self.popup.set_decorated(False)
        self.popup.set_has_frame(False)
        
        box = gtk.ScrolledWindow()
        box.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        self.tree = gtk.TreeView()
        self.tree.set_headers_visible(False)
        self.tree.set_hover_selection(True)

        bgcolor = gtk.Style().bg[gtk.STATE_NORMAL].to_string()
        time_cell = gtk.CellRendererPixbuf()
        time_cell.set_property("icon-name", "appointment-new")
        time_cell.set_property("cell-background", bgcolor)
        
        self.time_icon_column = gtk.TreeViewColumn("",
                                              time_cell)
        self.tree.append_column(self.time_icon_column)
        
        time_cell = gtk.CellRendererText()
        time_cell.set_property("scale", 0.8)
        time_cell.set_property("cell-background", bgcolor)

        self.time_column = gtk.TreeViewColumn("Time",
                                              time_cell,
                                              text = 3)
        self.tree.append_column(self.time_column)


        self.activity_column = gtk.TreeViewColumn("Activity",
                                                  gtk.CellRendererText(),
                                                  text=1)
        self.activity_column.set_expand(True)
        self.tree.append_column(self.activity_column)
        
        self.category_column = gtk.TreeViewColumn("Category",
                                                  stuff.CategoryCell(),
                                                  text=2)
        self.tree.append_column(self.category_column)



        self.tree.connect("button-press-event", self._on_tree_button_press_event)

        box.add(self.tree)
        self.popup.add(box)
        
        self.connect("button-press-event", self._on_button_press_event)
        self.connect("key-press-event", self._on_key_press_event)
        self.connect("key-release-event", self._on_key_release_event)
        self.connect("focus-in-event", self._on_focus_in_event)
        self.connect("focus-out-event", self._on_focus_out_event)
        self.connect("changed", self._on_text_changed)
        self.show()

    def populate_suggestions(self):
        self.activities = self.activities or runtime.storage.get_autocomplete_activities()
        self.categories = self.categories or runtime.storage.get_category_list()

        print self.filter, self.get_text()

        if self.filter == self.get_text():
            return #same thing, no need to repopulate
        
        self.filter = self.get_text()
        
        store = self.tree.get_model()
        if not store:
            store = gtk.ListStore(str, str, str, str)
            self.tree.set_model(store)            
        store.clear()
        
        for activity in self.activities:
            if self.filter == "" or activity['name'].startswith(self.filter): #self.filter in activity['name']:
                fillable = activity['name']
                if activity['category']:
                    fillable += "@%s" % activity['category']
                    
    
                store.append([fillable, activity['name'], activity['category'], '12:12'])


    def show_popup(self):
        result_count = self.tree.get_model().iter_n_children(None)
        if result_count == 0:
            self.popup.hide()
            return
        
        #move popup under the widget
        alloc = self.get_allocation()
        w = alloc.width

        window = self.get_parent_window()
        x, y= window.get_origin()
        
        #TODO - this is clearly unreliable as we calculate tree row size based on our gtk entry
        self.tree.parent.set_size_request(w,(alloc.height-6) * min([result_count, self.max_results]))
        self.popup.resize(w, (alloc.height-6) * min([result_count, self.max_results]))

        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)
        self.popup.show_all()
        
    def complete_inline(self):
        model = self.tree.get_model()
        if not self.filter or model.iter_n_children(None) == 0:
            return

        prefix_length = 0
        first_label = model[0][0]
        for i in range(len(self.filter), len(first_label)):
            letter_matching = all([row[0][i]==first_label[i] for row in model])
                
            if not letter_matching:
                break
            
            prefix_length +=1
        
        if prefix_length:
            prefix = first_label[len(self.filter):len(self.filter)+prefix_length]
            self.set_text("%s%s" % (self.filter, prefix))
            self.select_region(len(self.filter), len(self.filter) + prefix_length)



    def _on_text_changed(self, widget):
        self.news = True
        

    def _on_focus_in_event(self, entry, event):
        self.populate_suggestions()
        self.show_popup()

    def _on_focus_out_event(self, event, something):
        self.popup.hide()
        if self.news:
            self.emit("value-entered")
            self.news = False

    def _on_key_release_event(self, entry, event):
        if event.keyval not in (gtk.keysyms.Up, gtk.keysyms.Down, gtk.keysyms.Escape):
            self.populate_suggestions()
            self.show_popup()
            
            if event.keyval not in (gtk.keysyms.Delete, gtk.keysyms.BackSpace):
                self.complete_inline()

        


    def _on_key_press_event(self, entry, event):

        if event.keyval in (gtk.keysyms.Up, gtk.keysyms.Down):
            cursor = self.tree.get_cursor()
    
            if not cursor or not cursor[0]:
                self.tree.set_cursor(0)
                return True
            
            i = cursor[0][0]

            if event.keyval == gtk.keysyms.Up:
                i-=1
            elif event.keyval == gtk.keysyms.Down:
                i+=1

            # keep it in the sane borders
            i = min(max(i, 0), len(self.tree.get_model()) - 1)
            
            self.tree.set_cursor(i)
            self.tree.scroll_to_cell(i, use_align = True, row_align = 0.4)
            

        elif (event.keyval == gtk.keysyms.Return or
              event.keyval == gtk.keysyms.KP_Enter):
            
            if self.popup.get_property("visible"):
                self._on_selected()
            else:
                self._on_selected()
        elif (event.keyval == gtk.keysyms.Escape):
            self.popup.hide()
        else:
            return False
        
        return True
        
        
    def _on_button_press_event(self, button, event):
        self.popup.show()

    def _on_tree_button_press_event(self, tree, event):
        model, iter = tree.get_selection().get_selected()
        value = model.get_value(iter, 0)
        self.set_text(value)
        self._on_selected()

    def _on_selected(self):
        if self.news:
            self.emit("value-entered")
            self.news = False
            self.set_position(len(self.get_text()))
        

class MainWindow(object):
    def __init__(self):
        self._gui = stuff.load_ui_file("hamster.ui")
        self.window = self._gui.get_object('main-window')

        self.style_widgets()
        
        self.get_widget("tabs").set_current_page(1)

        self.set_last_activity()
        self.load_today()
        
        gtk.link_button_set_uri_hook(self.magic)
        
        self._gui.connect_signals(self)

    def magic(self, button, uri):
        print uri, button
        
    def style_widgets(self):
        #TODO - replace with the tree background color (can't get it atm!)
        self.get_widget("todays_activities_ebox").modify_bg(gtk.STATE_NORMAL,
                                                                 gtk.gdk.Color(65536.0,65536.0,65536.0))
        
        self.new_name = ActivityEntry() #widgets.HintEntry(_("Time and Name"), self.get_widget("new_name"))
        parent = self.get_widget("new_name").parent
        parent.remove(self.get_widget("new_name"))
        parent.add(self.new_name)
        
        self.new_description = widgets.HintEntry(_("Tags or Description"), self.get_widget("new_description"))
        

    def set_last_activity(self):
        activity = runtime.storage.get_last_activity()
        if activity:
            delta = dt.datetime.now() - activity['start_time']
            duration = delta.seconds /  60
            
            self.get_widget("last_activity_duration").set_text(stuff.format_duration(duration))
            self.get_widget("last_activity_name").set_text(activity['name'])
            if activity['category'] != _("Unsorted"):
                self.get_widget("last_activity_category") \
                    .set_text(" - %s" % activity['category'])
                self.get_widget("last_activity_category").show()
            else:
                self.get_widget("last_activity_category").hide()

            if activity['description']:
                self.get_widget("last_activity_description").set_text(activity['description'])
                self.get_widget("last_activity_description").show()
            else:
                self.get_widget("last_activity_description").hide()

    def load_today(self):
        todays_facts = runtime.storage.get_facts(dt.date.today())
        grid = self.get_widget("activities_today")
        
        #clear
        for child in grid.get_children(): grid.remove(child)
        

        def add_cell(cell, x, y, expandX = gtk.FILL,
                                 expandY = gtk.FILL):

            if isinstance(cell, str) or isinstance(cell, unicode):
                cell = gtk.Label(cell)
                cell.set_alignment(0.0, 0.0)
            
            grid.attach(cell, x, x + 1, y, y + 1, expandX, expandY)

            
        for rownum, fact in enumerate(todays_facts):
            if fact["end_time"]:
                fact_time = "%s - %s " % (fact["start_time"].strftime("%H:%M"),
                                       fact["end_time"].strftime("%H:%M"))
            else:
                fact_time = fact["start_time"].strftime("%H:%M ")

            duration = 24 * 60 * fact["delta"].days + fact["delta"].seconds / 60

            add_cell(fact_time, 0, rownum)

            name_tags = gtk.VBox()
            name_label = gtk.Label(fact['name'])
            name_label.set_alignment(0, 0)
            name_tags.pack_start(name_label)

            description_label = gtk.Label(fact['category'])
            description_label.set_alignment(0, 0)
            name_tags.pack_start(description_label)

            add_cell(name_tags, 1, rownum, (gtk.EXPAND | gtk.FILL), ())

            add_cell(stuff.format_duration(duration), 2, rownum, gtk.FILL, ())

            resume_button = gtk.LinkButton("resume:%d" % fact['id'])
            resume_button.set_label(_("Resume"))
            add_cell(resume_button, 3, rownum, (), ())

            resume_button = gtk.LinkButton("edit:%d" % fact['id'])
            resume_button.set_label(_("Edit"))
            add_cell(resume_button, 4, rownum, (), ())



        

    def on_switch_activity_clicked(self, widget):
        self.get_widget("new_entry_box").show()

    def show(self):
        self.window.show_all()
        
    def get_widget(self, name):
        return self._gui.get_object(name)
        
    

if __name__ == "__main__":
    gtk.window_set_default_icon_name("hamster-applet")
    MainWindow().show()
    
    gtk.main()    

