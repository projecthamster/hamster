# -*- coding: utf-8 -*-

# Copyright (C) 2007-2009 Toms Bauģis <toms.baugis at gmail.com>

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
import gobject

from hamster import dispatcher, storage, SHARED_DATA_DIR, stuff
from hamster import graphics, widgets
import hamster.eds

import time
import datetime as dt
import colorsys

import cairo, pango

""" TODO:
     * hook into notifications and refresh our days if some evil neighbour edit
       fact window has dared to edit facts
"""
class Dayline(graphics.Area):
    def __init__(self):
        graphics.Area.__init__(self)

        self.set_events(gtk.gdk.EXPOSURE_MASK
                                 | gtk.gdk.LEAVE_NOTIFY_MASK
                                 | gtk.gdk.BUTTON_PRESS_MASK
                                 | gtk.gdk.BUTTON_RELEASE_MASK
                                 | gtk.gdk.POINTER_MOTION_MASK
                                 | gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.connect("button_release_event", self.on_button_release)
        self.connect("motion_notify_event", self.draw_cursor)
        self.highlight_start, self.highlight_end = None, None
        self.drag_start = None
        self.move_type = ""
        self.on_time_changed = None #override this with your func to get notified when user changes date
        self.on_more_data = None #supplement with more data func that accepts single date
        self.in_progress = False

        self.range_start = None
        self.in_motion = False
        self.days = []
        
    
    def on_button_release(self, area, event):
        if not self.drag_start:
            return
        
        self.drag_start, self.move_type = None, None

        if event.state & gtk.gdk.BUTTON1_MASK:
            self.call_parent_time_changed()

    def set_in_progress(self, in_progress):
        self.in_progress = in_progress

    def call_parent_time_changed(self):
        #now calculate back from pixels into minutes
        start_time = self.get_value_at_pos(x = self.highlight_start)
        start_time = self.range_start.value + dt.timedelta(minutes = start_time) 
                
        end_time = self.get_value_at_pos(x = self.highlight_end) 
        end_time = self.range_start.value + dt.timedelta(minutes = end_time)
        if self.on_time_changed:
            self.on_time_changed(start_time, end_time)
        
    def scroll_to_range_start(self):
        if not self.in_motion:
            self.in_motion = True
            gobject.timeout_add(1000 / 30, self.animate_scale)
        
        
    def animate_scale(self):
        moving = self.range_start.update() > 5
        
        
        # check if maybe we are approaching day boundaries and should ask for
        # more data!
        if self.on_more_data:
            now = self.range_start.value
            date_plus = (now + dt.timedelta(hours = 12 + 2*4 + 1)).date()
            date_minus = (now - dt.timedelta(hours=1)).date()

            if date_minus != now.date() and date_minus not in self.days:
                self.facts += self.on_more_data(date_minus)
                self.days.append(date_minus)
            elif date_plus != now.date() and date_plus not in self.days:
                self.facts += self.on_more_data(date_plus)
                self.days.append(date_plus)
        
        
        self.redraw_canvas()
        if moving:
            return True
        else:
            self.in_motion = False
            self.call_parent_time_changed()

            return False


        
    def draw_cursor(self, area, event):
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state

        mouse_down = state & gtk.gdk.BUTTON1_MASK
            
        #print x, self.highlight_start, self.highlight_end
        if self.highlight_start != None:
            start_drag = 10 > (self.highlight_start - x) > -1

            end_drag = 10 > (x - self.highlight_end) > -1

            if start_drag and end_drag:
                start_drag = abs(x - self.highlight_start) < abs(x - self.highlight_end)

            in_between = self.highlight_start <= x <= self.highlight_end
            scale = True

            if self.in_progress:
                end_drag = False
                in_between = False
                scale = False

            if mouse_down and not self.drag_start:
                self.drag_start = x
                if start_drag:
                    self.move_type = "start"
                elif end_drag:
                    self.move_type = "end"
                elif in_between:
                    self.move_type = "move"
                    self.drag_start = x - self.highlight_start
                elif scale:
                    self.move_type = "scale_drag"
                    self.drag_start_time = self.range_start.value

            
            if mouse_down and self.drag_start:
                start, end = 0, 0
                if self.move_type == "start":
                    if 0 <= x <= self.width:
                        start = x
                        end = self.highlight_end
                elif self.move_type == "end":
                    if 0 <= x <= self.width:
                        start = self.highlight_start
                        end = x
                elif self.move_type == "move":
                    width = self.highlight_end - self.highlight_start
                    start = x - self.drag_start
                    start = max(0, min(start, self.width))
                    
                    end = start + width
                    if end > self.width:
                        end = self.width
                        start = end - width

                if end - start > 1:
                    self.highlight_start = start
                    self.highlight_end = end
                    self.redraw_canvas()

                if self.move_type == "scale_drag":
                    self.range_start.target(self.drag_start_time +
                                            dt.timedelta(minutes = self.get_value_at_pos(x = self.drag_start) - self.get_value_at_pos(x = x)))
                    self.scroll_to_range_start()

                self.call_parent_time_changed()

            if start_drag:
                area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.LEFT_SIDE))
            elif end_drag:
                area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.RIGHT_SIDE))
            elif in_between:
                area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))
            else:
                area.window.set_cursor(None)
                
        
    def draw(self, day_facts, highlight = None):
        """Draw chart with given data"""
        self.facts = day_facts
        if self.facts:
            self.days.append(self.facts[0]["start_time"].date())
        
        start_time = highlight[0] - dt.timedelta(minutes = highlight[0].minute) - dt.timedelta(hours = 10)
        
        self.range_start = graphics.Integrator(start_time, damping = 0.5, attraction = 0.7)

        self.highlight = highlight
        
        self.show()
        
        self.redraw_canvas()


    def _minutes_from_start(self, date):
            delta = (date - self.range_start.value)
            return delta.days * 24 * 60 + delta.seconds / 60
            
    def _render(self):
        context = self.context
        #TODO - use system colors and fonts
 
        context.set_line_width(1)

        #we will buffer 4 hours to both sides so partial labels also appear
        range_end = self.range_start.value + dt.timedelta(hours = 12 + 2 * 4)        
        self.graph_x = -self.width / 3 #so x moves one third out of screen
        self.set_value_range(x_min = 0, x_max = 12 * 60)

        minutes = self._minutes_from_start(range_end)



        graph_y = 4
        graph_height = self.height - 25
        graph_y2 = graph_y + graph_height

        
        # graph area
        self.fill_area(0, graph_y - 1, self.width, graph_height, (1,1,1))
        context.set_source_rgb(0.7, 0.7, 0.7)
        context.rectangle(0, graph_y-1, self.width - 1, graph_height)
        context.stroke()
    
        #time scale

        #scale labels
        context.set_source_rgb(0, 0, 0)
        for i in range(minutes):
            label_time = (self.range_start.value + dt.timedelta(minutes=i))
            if label_time.minute == 0 and label_time.hour % 2 == 0:
                if label_time.hour == 0:
                    context.set_source_rgb(0.8, 0.8, 0.8)
                    self.move_to(i, graph_y)
                    self.line_to(i, graph_y2)
                    label_minutes = label_time.strftime("%b %d.")
                else:
                    label_minutes = label_time.strftime("%H:%M")

                context.set_source_rgb(0, 0, 0)
                self.layout.set_text(label_minutes)
                label_w, label_h = self.layout.get_pixel_size()
                
                context.move_to(self.get_pixel(x_value=i) - label_w/2,
                                graph_y2 + 6)                

                context.show_layout(self.layout)
        context.stroke()
        
        #bars
        context.set_source_rgba(0.86, 0.86, 0.86, 0.5)
        for fact in self.facts:
            start_minutes = self._minutes_from_start(fact["start_time"])
            
            if fact["end_time"]:
                end_minutes = self._minutes_from_start(fact["end_time"])
            else:
                if fact["start_time"].date() == dt.date.today():
                    end_minutes = self._minutes_from_start(dt.datetime.now())
            
            if self.get_pixel(x_value = end_minutes) > 0 and \
                self.get_pixel(x_value = start_minutes) < self.width:
                    context.rectangle(self.get_pixel(x_value = start_minutes), graph_y,
                                      self.get_pixel(x_value=end_minutes) - self.get_pixel(x_value=start_minutes), graph_height - 1)
        context.fill()
        
        

        if self.highlight:
            self.highlight_start =self.get_pixel(x_value= self._minutes_from_start(self.highlight[0]))
            self.highlight_end = self.get_pixel(x_value=self._minutes_from_start(self.highlight[1]))
            self.highlight = None


        #highlight rectangle
        if self.highlight_start != None:
            rgb = colorsys.hls_to_rgb(.6, .7, .5)
            context.set_source_rgba(rgb[0], rgb[1], rgb[2], 0.5)

            context.rectangle(self.highlight_start, graph_y-3,
                              self.highlight_end - self.highlight_start, graph_height + 4)
            context.fill_preserve()
            context.set_source_rgb(*rgb)
            context.stroke()
        
        if self.move_type == "move" and (self.highlight_start == 0 or self.highlight_end == self.width):
            if self.highlight_start == 0:
                self.range_start.target(self.range_start.value - dt.timedelta(minutes=30))
            if self.highlight_end == self.width:
                self.range_start.target(self.range_start.value + dt.timedelta(minutes=30))
            self.scroll_to_range_start()



class CustomFactController:
    def __init__(self,  parent = None, fact_date = None, fact_id = None):
        self._gui = stuff.load_ui_file("edit_activity.ui")
        self.window = self.get_widget('custom_fact_window')

        self.parent, self.fact_id = parent, fact_id

        start_date, end_date = None, None
        if fact_id:
            fact = storage.get_fact(fact_id)

            label = fact['name']
            if fact['category'] != _("Unsorted"):
                label += "@%s" %  fact['category']
            self.get_widget('activity_combo').child.set_text(label)
            
            start_date = fact["start_time"]
            end_date = fact["end_time"]
            
            buf = gtk.TextBuffer()
            buf.set_text(fact["description"] or "")
            self.get_widget('description').set_buffer(buf)

            if not end_date:
                self.get_widget("in_progress").set_active(True)
                if (dt.datetime.now() - start_date).days == 0:
                    end_date = dt.datetime.now()

            self.get_widget("save_button").set_label("gtk-save")
            self.window.set_title(_("Update activity"))

        elif fact_date and fact_date != dt.date.today():
            # if there is previous activity with end time - attach to it
            # otherwise let's start at 8am
            last_activity = storage.get_facts(fact_date)
            if last_activity and last_activity[len(last_activity)-1]["end_time"]:
                start_date = last_activity[len(last_activity)-1]["end_time"]
            else:
                start_date = dt.datetime(fact_date.year, fact_date.month,
                                         fact_date.day, 8)

        start_date = start_date or dt.datetime.now()
        end_date = end_date or start_date + dt.timedelta(minutes = 30)


        self.start_date = widgets.DateInput(start_date)
        self.get_widget("start_date_placeholder").add(self.start_date)
        self.start_date.connect("date-entered", self.validate_fields)

        self.start_time = widgets.TimeInput(start_date)
        self.get_widget("start_time_placeholder").add(self.start_time)
        self.start_time.connect("time-entered", self.on_start_time_entered)
        
        self.end_time = widgets.TimeInput(end_date, start_date)
        self.get_widget("end_time_placeholder").add(self.end_time)
        self.end_time.connect("time-entered", self.on_end_time_entered)
        self.set_end_date_label(end_date)


        self.set_dropdown()
        self.refresh_menu()

        self.dayline = Dayline()
        self.dayline.on_time_changed = self.update_time
        self.dayline.on_more_data = storage.get_facts
        self._gui.get_object("day_preview").add(self.dayline)

        self.on_in_progress_toggled(self.get_widget("in_progress"))
        self._gui.connect_signals(self)

    def update_time(self, start_time, end_time):
        self.start_time.set_time(start_time)
        self.start_date.set_date(start_time)
        self.end_time.set_time(end_time)
        self.set_end_date_label(end_time)

        
    def draw_preview(self, date, highlight = None):
        day_facts = storage.get_facts(date)
        self.dayline.draw(day_facts, highlight)
        
        

    def set_dropdown(self):
        # set up drop down menu
        self.activity_list = self._gui.get_object('activity_combo')
        self.activity_list.set_model(gtk.ListStore(gobject.TYPE_STRING,
                                                   gobject.TYPE_STRING,
                                                   gobject.TYPE_STRING))


        self.activity_list.set_property("text-column", 2)
        self.activity_list.clear()
        activity_cell = gtk.CellRendererText()
        self.activity_list.pack_start(activity_cell, True)
        self.activity_list.add_attribute(activity_cell, 'text', 0)
        category_cell = stuff.CategoryCell()  
        self.activity_list.pack_start(category_cell, False)
        self.activity_list.add_attribute(category_cell, 'text', 1)
        
        self.activity_list.child.connect('key-press-event', self.on_activity_list_key_pressed)


        # set up autocompletition
        self.activities = gtk.ListStore(gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING)
        completion = gtk.EntryCompletion()
        completion.set_model(self.activities)

        activity_cell = gtk.CellRendererText()
        completion.pack_start(activity_cell, True)
        completion.add_attribute(activity_cell, 'text', 0)
        completion.set_property("text-column", 2)

        category_cell = stuff.CategoryCell()  
        completion.pack_start(category_cell, False)
        completion.add_attribute(category_cell, 'text', 1)

        completion.set_minimum_key_length(1)
        completion.set_inline_completion(True)

        self.activity_list.child.set_completion(completion)
        

    def refresh_menu(self):
        #first populate the autocomplete - contains all entries in lowercase
        self.activities.clear()
        all_activities = storage.get_autocomplete_activities()
        for activity in all_activities:
            activity_category = activity['name']
            if activity['category']:
                activity_category += "@%s" % activity['category']
            self.activities.append([activity['name'],
                                    activity['category'],
                                    activity_category])


        #now populate the menu - contains only categorized entries
        store = self.activity_list.get_model()
        store.clear()

        #populate fresh list from DB
        categorized_activities = storage.get_sorted_activities()

        for activity in categorized_activities:
            activity_category = activity['name']
            if activity['category']:
                activity_category += "@%s" % activity['category']
            item = store.append([activity['name'],
                                 activity['category'],
                                 activity_category])

        # finally add TODO tasks from evolution to both lists
        tasks = hamster.eds.get_eds_tasks()
        for activity in tasks:
            activity_category = "%s@%s" % (activity['name'], activity['category'])
            self.activities.append([activity['name'],activity['category'],activity_category])
            store.append([activity['name'], activity['category'], activity_category])

        return True

    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)

    def show(self):
        self.window.show()

    def _get_datetime(self, prefix):
        start_time = self.start_time.get_time()
        start_date = self.start_date.get_date()

        if prefix == "end":
            end_time = self.end_time.get_time()
            end_date = start_date
            if end_time < start_time:
                end_date = start_date + dt.timedelta(days=1)
            self.set_end_date_label(end_date)
            time, date = end_time, end_date
        else:
            time, date = start_time, start_date
        
        if time and date:
            return dt.datetime.combine(date, time.time())
        else:
            return None
    
    def figure_description(self):
        activity = self.get_widget("activity_combo").child.get_text().decode("utf-8")

        # juggle with description - break into parts and then put together
        buf = self.get_widget('description').get_buffer()
        description = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), 0)\
                         .decode("utf-8")
        description = description.strip()
        
        # user might also type description in the activity name - strip it here
        # and remember value
        inline_description = None
        if activity.find(",") != -1:
            activity, inline_description  = activity.split(",", 1)
            inline_description = inline_description.strip()
        
        # description field is prior to inline description
        return description or inline_description
        
    def on_save_button_clicked(self, button):
        activity = self.get_widget("activity_combo").child.get_text().decode("utf-8")
        
        if not activity:
            return False

        description = self.figure_description()

        if description:
            activity = "%s, %s" % (activity, description)

        
        start_time = self._get_datetime("start")

        if self.get_widget("in_progress").get_active():
            end_time = None
        else:
            end_time = self._get_datetime("end")

        # we don't do updates, we do insert/delete. So now it is time to delete
        if self.fact_id:
            storage.remove_fact(self.fact_id)

        storage.add_fact(activity, start_time, end_time)


        # hide panel only on add - on update user will want to see changes
        if not self.fact_id: 
            dispatcher.dispatch('panel_visible', False)
        
        self.close_window()
    
    def on_activity_list_key_pressed(self, entry, event):
        #treating tab as keydown to be able to cycle through available values
        if event.keyval == gtk.keysyms.Tab:
            event.keyval = gtk.keysyms.Down
        return False
        
    def on_in_progress_toggled(self, check):
        sensitive = not check.get_active()
        self.end_time.set_sensitive(sensitive)
        self.get_widget("end_label").set_sensitive(sensitive)
        self.get_widget("end_date_label").set_sensitive(sensitive)
        self.validate_fields()
        self.dayline.set_in_progress(not sensitive)

    def on_cancel_clicked(self, button):
        self.close_window()
        
    def on_activity_combo_changed(self, combo):
        self.validate_fields()

    def on_start_time_entered(self, widget):
        self.end_time.set_time(self.start_time.get_time() +
                                                     dt.timedelta(minutes = 30))
        self.end_time.set_start_time(self.start_time.get_time())
        self.validate_fields()
        
    def on_end_time_entered(self, widget):
        self.validate_fields()
    
    def set_end_date_label(self, some_date):
        self.get_widget("end_date_label").set_text(some_date.strftime("%x"))
    
    def validate_fields(self, widget = None):
        activity_text = self.get_widget("activity_combo").child.get_text()
        start_time = self._get_datetime("start")

        end_time = self._get_datetime("end")
        if self.get_widget("in_progress").get_active():
            end_time = dt.datetime.now()

        # if we are too far, just roll back for one day
        if ((end_time - start_time).days > 0): 
            end_time -= dt.timedelta(days=1)
            self.update_time(start_time, end_time)

        if start_time:
            self.draw_preview(start_time.date(), [start_time, end_time])

        # if end time is not in proper distance, do the brutal +30 minutes reset
        if (end_time < start_time or (end_time - start_time).days > 0):
            end_time = start_time + dt.timedelta(minutes = 30)
            self.update_time(start_time, end_time)

        looks_good = False
        if activity_text != "" and start_time and end_time and \
           (end_time - start_time).days == 0:
            looks_good = True

        self.get_widget("save_button").set_sensitive(looks_good)

    def on_window_key_pressed(self, tree, event_key):
        if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w 
              and event_key.state & gtk.gdk.CONTROL_MASK)):
            
            if self.start_date.popup.get_property("visible") or \
               self.start_time.popup.get_property("visible") or \
               self.end_time.popup.get_property("visible"):
                return False

            self.close_window()            

    def on_close(self, widget, event):
        self.close_window()        

    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            return False
        
