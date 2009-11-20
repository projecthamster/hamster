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
import widgets, stuff

import gobject

import graphics
import pango, cairo

from math import pi

class TagEntry(graphics.Area):
    def __init__(self):
        graphics.Area.__init__(self)
        self.font_size = 10
        self.connect("mouse-over", self.on_tag_hover)
        self.connect("button-release", self.on_tag_click)
        self.hover_tag = None
        self.selected_tags = []

    def on_tag_hover(self, widget, regions):
        if regions:
            self.hover_tag = regions[0]
        else:
            self.hover_tag = None
        
        self.redraw_canvas()
    
    def on_tag_click(self, widget, regions):
        tag = regions[0]
        if tag in self.selected_tags:
            self.selected_tags.remove(tag)
        else:
            self.selected_tags.append(tag)

        self.redraw_canvas()
        
    def draw(self):
        """Draw chart with given data"""
        self.show()        
        self.redraw_canvas()

    def tag_size(self, label):
        text_w, text_h = self.set_text(label)
        w = text_w + 18 # padding (we have some diagonals to draw)
        h = text_h + 4
        return w, h
        
        
    def draw_tag(self, label, x, y, color):
        self.context.set_line_width(1)

        tag_x = x + 0.5
        tag_y = y + 0.5

        w, h = self.tag_size(label)
                
        self.move_to(x, y + 6)
        self.line_to(x + 6, y)
        self.line_to(x + w, y)
        self.line_to(x + w, y + h)
        self.line_to(x + 6, y + h)
        self.line_to(x, y + h - 6)
        self.line_to(x, y + 6)
        self.set_color(color)
        self.context.fill_preserve()
        self.set_color((200, 200, 200))
        self.context.stroke()

        self.context.set_antialias(cairo.ANTIALIAS_DEFAULT)
        self.context.arc(x + 6, y + h / 2 + 1, 2, 0, 2 * pi)
        self.set_color((255, 255, 255))
        self.context.fill_preserve()
        self.set_color((200, 200, 200))
        self.context.stroke()
        self.context.set_antialias(cairo.ANTIALIAS_NONE)

        self.set_color((0, 0, 0))

        #self.layout.set_width((self.width) * pango.SCALE)
        self.context.move_to(x + 12,y + 2)
        
        self.context.show_layout(self.layout)
        
    
    def _render(self):
        self.fill_area(0, 0, self.width, self.height, (255,255,255))
        
        tags = ["peh", "poh", "and so on", "etc", "true magic",
                "and so we go", "on and on", "until you drop",  "somewhere",
                "and forget", "what we", "were", "actually doing"]
        
        cur_x, cur_y = 5, 5
        for tag in tags:
            w, h = self.tag_size(tag)
            if cur_x + w >= self.width - 5:  #if we don't fit, we wrap
                cur_x = 5
                cur_y += h + 6
            
            if tag in self.selected_tags:
                color = (242, 229, 97)
            elif tag == self.hover_tag:
                color = (252, 248, 204)
            else:
                color = (241, 234, 170)
            
            self.draw_tag(tag, cur_x, cur_y, color)
            self.register_mouse_region(cur_x, cur_y, cur_x + w, cur_y + h, tag)

            cur_x += w + 8 #some padding too, please

        

        

class MainWindow(object):
    def __init__(self):
        self._gui = stuff.load_ui_file("hamster.ui")
        self.window = self._gui.get_object('main-window')

        self.style_widgets()
        
        self.get_widget("tabs").set_current_page(0)

        self.set_last_activity()
        self.load_today()
        
        gtk.link_button_set_uri_hook(self.magic)
        
        self.tag_box = TagEntry()
        self.get_widget("tag_box").add(self.tag_box)
        
        self._gui.connect_signals(self)
        

    def magic(self, button, uri):
        print uri, button
        
    def style_widgets(self):
        #TODO - replace with the tree background color (can't get it atm!)
        self.get_widget("todays_activities_ebox").modify_bg(gtk.STATE_NORMAL,
                                                                 gtk.gdk.Color(65536.0,65536.0,65536.0))
        
        self.new_name = widgets.ActivityEntry()
        widgets.add_hint(self.new_name, _("Time and Name"))
        parent = self.get_widget("new_name").parent
        parent.remove(self.get_widget("new_name"))
        parent.add(self.new_name)
        
        self.new_description = self.get_widget("new_description")
        widgets.add_hint(self.new_description, _("Tags or Description"))
        

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

