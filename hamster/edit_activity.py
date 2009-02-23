# -*- coding: utf-8 -*-

# Copyright (C) 2007, 2008 Toms Bauģis <toms.baugis at gmail.com>

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
import re

from hamster import dispatcher, storage, SHARED_DATA_DIR, stuff
import hamster.eds

import time
import datetime
import colorsys

GLADE_FILE = "edit_activity.glade"

import cairo, pango
class Dayline(gtk.DrawingArea):
    def __init__(self, **args):
        gtk.DrawingArea.__init__(self)
        self.context = None
        self.layout = None
        self.connect("expose_event", self._expose)

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

    def on_button_release(self, area, event):
        if event.state & gtk.gdk.BUTTON1_MASK:
            if self.drag_start:
                self.drag_start = None
                #now calculate back from pixels into minutes
                
                start_minutes = int(self.highlight_start / self.minute_pixel) 
                end_minutes = int(self.highlight_end / self.minute_pixel) 
                
                print start_minutes / 60, start_minutes % 60
                print end_minutes / 60, end_minutes % 60
                self.highlight = [
                    datetime.time(start_minutes / 60, start_minutes % 60),
                    datetime.time(end_minutes / 60, end_minutes % 60)
                ]
                

        
    def draw_cursor(self, area, event):
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state

        mouse_down = state & gtk.gdk.BUTTON1_MASK
            
        #print x, self.highlight_start, self.highlight_end
        if self.highlight_start:
            start_drag = abs(x - self.highlight_start) < 5
            end_drag = abs(x - self.highlight_end) < 5
            if start_drag and end_drag:
                start_drag = abs(x - self.highlight_start) < abs(x - self.highlight_end)

            in_between = self.highlight_start <= x <= self.highlight_end
                
            
            if mouse_down and not self.drag_start:
                self.drag_start = x
                if start_drag:
                    self.move_type = "start"
                elif end_drag:
                    self.move_type = "end"
                elif in_between:
                    self.move_type = "move"
                    self.drag_start = x - self.highlight_start
                else:
                    self.move_type = None
                    self.drag_start = None

            
            if mouse_down and self.drag_start:
                x = max(0, min(x, 60*24 / self.minute_pixel))
                start, end = 0, 0
                if self.move_type == "start":
                    start = x
                elif self.move_type == "end":
                    end = x
                elif self.move_type == "move":
                    width = self.highlight_end - self.highlight_start
                    start = x - self.drag_start
                    end = self.highlight_start + width
                    
                start = max(0, min(start, (60*23+59) * self.minute_pixel))
                end = max(0, min(end, (60*23+59) * self.minute_pixel))
                
                if (end - start) > 10:
                    print "zzzzzzzzzzzzzz", start, end
                    self.highlight_start = start
                    self.highlight_end = end
                    self._invalidate()

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
        self.highlight = highlight
        self.show()
        
        self._invalidate()


    def _invalidate(self):
        """Force graph redraw"""
        if self.window:    #this can get called before expose    
            alloc = self.get_allocation()
            rect = gtk.gdk.Rectangle(alloc.x, alloc.y, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)            


    def _expose(self, widget, event):
        """expose is when drawing's going on, like on _invalidate"""
        self.context = widget.window.cairo_create()
        self.context.set_antialias(cairo.ANTIALIAS_NONE)

        self.context.rectangle(event.area.x, event.area.y,
                               event.area.width, event.area.height)
        self.context.clip()
        
        alloc = self.get_allocation()  #x, y, width, height
        self.width = alloc.width
        self.height = alloc.height
        self._draw(self.context)

        return False

    def _draw(self, context):
        #TODO - use system colors and fonts
 
        context.set_line_width(1)

        self.minute_pixel = self.width / float(60 * 24)

        if self.highlight:
            self.highlight_start = (self.highlight[0].hour * 60 + self.highlight[0].minute) * self.minute_pixel
            self.highlight_end = (self.highlight[1].hour * 60 + self.highlight[1].minute)  * self.minute_pixel
            self.highlight = None

        minute_pixel = self.minute_pixel        
        
        #run from end to beginning so the rectangle fillings do not erase text
        self.facts.reverse()

        graph_y = 1
        graph_height = self.height - 15


        
        context.set_source_rgb(1, 1, 1)
        context.rectangle(0, graph_y-1, self.width, graph_height)
        context.fill()
        context.set_source_rgb(0.7, 0.7, 0.7)
        context.rectangle(0, graph_y-1, self.width-1, graph_height)
        context.stroke()

        
        context.set_source_rgb(0.86, 0.86, 0.86)
        for fact in self.facts:
            start_minutes = fact["start_time"].hour * 60 \
                                                    + fact["start_time"].minute

            if fact["end_time"]:
                end_minutes = fact["end_time"].hour * 60 \
                                                      + fact["end_time"].minute
            else:
                end_minutes = start_minutes
            
            context.rectangle(minute_pixel * start_minutes, graph_y,
                              minute_pixel * (end_minutes - start_minutes), graph_height - 1)
        context.fill()


        #highlight rectangle
        if self.highlight_start:
            rgb = colorsys.hls_to_rgb(.6, .7, .5)
            context.set_source_rgba(rgb[0], rgb[1], rgb[2], 0.5)

            context.rectangle(self.highlight_start, graph_y-1,
                              self.highlight_end - self.highlight_start, graph_height)
            context.fill_preserve()
            context.set_source_rgb(*rgb)
            context.stroke()
            

        #scale labels
        context.set_source_rgb(0, 0, 0)
        for i in range(0, 24, 4):
            context.move_to(minute_pixel * i * 60, graph_height + 12)

            context.show_text("%s:00" % i)

        context.stroke()





class CustomFactController:
    def __init__(self,  fact_date = None, fact_id = None):
        self.glade = gtk.glade.XML(os.path.join(SHARED_DATA_DIR, GLADE_FILE))
        self.window = self.get_widget('custom_fact_window')

        # build the menu
        self.fact_id = fact_id

        self.set_dropdown()
        self.refresh_menu()

        self.get_widget("in_progress").set_active(False)
        end_date = None

        if fact_id:
            fact = storage.get_fact(fact_id)
            print fact
            self.get_widget('activity_text').set_text(fact["name"])
            
            start_date = fact["start_time"]
            end_date = fact["end_time"]
            
            buf = gtk.TextBuffer()
            buf.set_text(fact["description"] or "")
            self.get_widget('description').set_buffer(buf)

            if not fact["end_time"] and fact["start_time"].date() == datetime.datetime.today():
                self.get_widget("in_progress").set_active(True)

            self.get_widget("save_button").set_label("gtk-save")
            self.window.set_title(_("Update activity"))

        elif fact_date and fact_date != datetime.date.today():
            # we are asked to add task in some day, but time has not
            # been specified - two things we can do
            # if there is end time of last activity, then we start from there
            # if end time is missing, or there are no activities at all
            # then we start from 8am (pretty default)
            last_activity = storage.get_facts(fact_date)
            if last_activity and last_activity[len(last_activity)-1]["end_time"]:
                start_date = last_activity[len(last_activity)-1]["end_time"]
            else:
                if fact_date == datetime.date.today():
                    # for today time is now
                    start_date = datetime.datetime.now()
                else:
                    # for other days it is 8am
                    start_date = datetime.datetime(fact_date.year,
                                                  fact_date.month,
                                                  fact_date.day,
                                                  8)
        else:
            start_date = datetime.datetime.now()
            end_date = start_date + datetime.timedelta(minutes = 30)

        self.dayline = Dayline()
        self.glade.get_widget("day_preview").add(self.dayline)

        self.get_widget('start_date').set_text(self.format_date(start_date))
        self.get_widget('start_time').set_text(self.format_time(start_date))
        
        self.get_widget('end_date').set_text(self.format_date(end_date))
        self.get_widget('end_time').set_text(self.format_time(end_date))

        self.on_in_progress_toggled(self.get_widget("in_progress"))

        self.init_calendar_window()
        self.init_time_window()

        self.glade.signal_autoconnect(self)

    def draw_preview(self, date, highlight = None):
        day_facts = storage.get_facts(date)
        self.dayline.draw(day_facts, highlight)
        
        
    def init_calendar_window(self):
        self.calendar_window = self.glade.get_widget('calendar_window')
        self.date_calendar = gtk.Calendar()
        #self.date_calendar.mark_day(datetime.date.today().day) #mark day marks day in all months, hahaha
        self.date_calendar.connect("day-selected", self.on_day_selected)
        self.date_calendar.connect("day-selected-double-click", self.on_day_selected_double_click)
        self.date_calendar.connect("button-press-event", self.on_cal_button_press_event)
        self.glade.get_widget("calendar_box").add(self.date_calendar)

    def on_cal_button_press_event(self, calendar, event):
        self.prev_cal_day = calendar.get_date()[2]

    def on_day_selected_double_click(self, calendar):
        self.prev_cal_day = None
        self.on_day_selected(calendar) #forward
        
    def on_day_selected(self, calendar):
        if self.prev_cal_day == calendar.get_date()[2]:
            return
        
        cal_date = calendar.get_date()

        date = datetime.date(cal_date[0], cal_date[1] + 1, cal_date[2])
        
        widget = None
        if self.get_widget("start_date").is_focus():
            widget = self.get_widget("start_date")
        elif self.get_widget("end_date").is_focus():
            widget = self.get_widget("end_date")
            
        if widget:
            widget.set_text(self.format_date(date))

        self.calendar_window.hide()        
        self.validate_fields()
        
    def init_time_window(self):
        self.time_window = self.glade.get_widget('time_window')
        self.time_tree = self.get_widget('time_tree')
        self.time_tree.append_column(gtk.TreeViewColumn("Time", gtk.CellRendererText(), text=0))


    def on_date_button_press_event(self, button, event):
        if self.calendar_window.get_property("visible"):
            self.calendar_window.hide()

    def on_time_button_press_event(self, button, event):
        if self.time_window.get_property("visible"):
            self.time_window.hide()
        
        
    def figure_time(self, str_time):
        # strip everything non-numeric and consider hours to be first number
        # and minutes - second number
        numbers = re.split("\D", str_time)
        numbers = filter(lambda x: x!="", numbers)
        hours, minutes = None, None
        
        if len(numbers) >= 1:
            hours = int(numbers[0])
            
        if len(numbers) >= 2:
            minutes = int(numbers[1])
            
        if (hours == None and minutes == None) or hours > 24 or minutes > 60:
            return None #no can do

        """ this breaks 24 hour mode, when hours are given
        #if hours specified in 12 hour mode, default to PM
        #TODO - laame, show me how to do this better, pleease
        am = datetime.time(1, 00).strftime("%p")
        if hours <= 11 and str_time.find(am) < 0:
            hours += 12
        """
        
        return datetime.datetime(1900, 1, 1, hours, minutes)


    def set_dropdown(self):
        # set up drop down menu
        self.activity_list = self.glade.get_widget('activity_combo')
        self.activity_list.set_model(gtk.ListStore(gobject.TYPE_STRING,
                                                   gobject.TYPE_STRING,
                                                   gobject.TYPE_STRING))

        self.activity_list.clear()
        activity_cell = gtk.CellRendererText()
        self.activity_list.pack_start(activity_cell, True)
        self.activity_list.add_attribute(activity_cell, 'text', 0)
        category_cell = stuff.CategoryCell()  
        self.activity_list.pack_start(category_cell, False)
        self.activity_list.add_attribute(category_cell, 'text', 1)
        
        self.activity_list.set_property("text-column", 2)


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

        def match_func(completion, key, iter):
            model = completion.get_model()
            text = model.get_value(iter, 2)
            if text and text.startswith(key):
                return True
            return False

        completion.set_match_func(match_func)
        completion.set_minimum_key_length(1)
        completion.set_inline_completion(True)

        self.activity_list.child.set_completion(completion)
        

    def refresh_menu(self):
        #first populate the autocomplete - contains all entries in lowercase
        self.activities.clear()
        all_activities = storage.get_autocomplete_activities()
        for activity in all_activities:
            activity_category = "%s@%s" % (activity['name'], activity['category'])
            self.activities.append([activity['name'],
                                    activity['category'],
                                    activity_category])


        #now populate the menu - contains only categorized entries
        store = self.activity_list.get_model()
        store.clear()

        #populate fresh list from DB
        categorized_activities = storage.get_sorted_activities()

        for activity in categorized_activities:
            activity_category = "%s@%s" % (activity['name'], activity['category'])
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
        return self.glade.get_widget(name)

    def show(self):
        self.window.show()

    def _get_datetime(self, prefix):
        # adds symbolic time to date in seconds
        date = self.figure_date(self.get_widget(prefix + '_date').get_text())
        time = self.figure_time(self.get_widget(prefix + '_time').get_text())
        
        if time and date:
            return datetime.datetime.combine(date, time.time())
        else:
            return None
    
    def figure_description(self):
        activity = self.get_widget("activity_text").get_text().decode("utf-8")

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
        activity = self.get_widget("activity_text").get_text().decode("utf-8")
        
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


        storage.add_fact(activity, start_time, end_time)

        # we don't do updates, we do insert/delete. So now it is time to delete
        if self.fact_id:
            storage.remove_fact(self.fact_id)


        # hide panel only on add - on update user will want to see changes
        if not self.fact_id: 
            dispatcher.dispatch('panel_visible', False)
        
        self.window.destroy()
    
    def figure_date(self, date_str):
        if not date_str:
            return ""
        
        return datetime.datetime.strptime(date_str, "%x")

    def format_date(self, date):
        if not date:
            return ""
        else:
            return date.strftime("%x")
    
    def on_date_focus_in_event(self, entry, event):
        window = entry.get_parent_window()
        x, y= window.get_origin()

        alloc = entry.get_allocation()
        
        date = self.figure_date(entry.get_text())
        if date:
            self.prev_cal_day = date.day #avoid 
            self.date_calendar.select_month(date.month-1, date.year)
            self.date_calendar.select_day(date.day)
        
        self.calendar_window.move(x + alloc.x,y + alloc.y + alloc.height)
        self.calendar_window.show_all()

    def on_date_focus_out_event(self, event, something):
        self.calendar_window.hide()
        self.validate_fields()
    

    def on_start_time_focus_in_event(self, entry, event):
        self.show_time_window(entry)

    def on_start_time_focus_out_event(self, event, something):
        self.time_window.hide()
        self.validate_fields()
        
    def on_end_time_focus_in_event(self, entry, event):
        start_time = self.figure_time(self.get_widget("start_time").get_text())
        self.show_time_window(entry, start_time)

    def on_end_time_focus_out_event(self, event, something):
        self.time_window.hide()
        self.validate_fields()
    
    def on_in_progress_toggled(self, check):
        self.get_widget("end_time").set_sensitive(not check.get_active())
        self.get_widget("end_date").set_sensitive(not check.get_active())
        self.validate_fields()

    def show_time_window(self, widget, start_time = None):

        focus_time = self.figure_time(widget.get_text())
        
        hours = gtk.ListStore(gobject.TYPE_STRING)
        
        # populate times
        i_time = start_time or datetime.datetime(1900, 1, 1, 0, 0)
        
        if focus_time and focus_time < i_time:
            focus_time += datetime.timedelta(days = 1)
        
        if start_time:
            end_time = i_time + datetime.timedelta(hours = 12)
        else:
            end_time = i_time + datetime.timedelta(hours = 24)
        
        i, focus_row = 0, None
        while i_time < end_time:
            row_text = self.format_time(i_time)
            if start_time:
                delta = (i_time - start_time).seconds / 60
                
                if delta % 60 == 0:
                    delta_text = "%dh" % (delta / 60.0)
                elif delta / 60 == 0:
                    delta_text = "%dmin" % (delta % 60.0)
                else:
                    delta_text = "%dh %dmin" % (delta / 60.0, delta % 60)

                row_text = "%s (%s)" % (row_text, delta_text)

            hours.append([row_text])
            
            
            if focus_time and i_time <= focus_time <= i_time + datetime.timedelta(minutes = 30):
                focus_row = i
            
            i += 1

            if start_time:
                i_time += datetime.timedelta(minutes = 15)
            else:
                i_time += datetime.timedelta(minutes = 30)

            


        self.time_tree.set_model(hours)        


        #focus on row
        if focus_row != None:
            self.time_tree.set_cursor(focus_row)
            self.time_tree.scroll_to_cell(focus_row, use_align = True, row_align = 0.4)
        


        #move popup under the widget
        alloc = widget.get_allocation()
        w = alloc.width
        if start_time:
            w = w * 2
        self.time_tree.set_size_request(w, alloc.height * 5)

        window = widget.get_parent_window()
        x, y= window.get_origin()

        self.time_window.move(x + alloc.x,y + alloc.y + alloc.height)
        self.time_window.show_all()

    
    def on_date_key_press_event(self, entry, event):
        cal_date = self.date_calendar.get_date()
        date = datetime.date(cal_date[0], cal_date[1]+1, cal_date[2])
        enter_pressed = False

        if event.keyval == gtk.keysyms.Up:
            date = date - datetime.timedelta(days=1)
        elif event.keyval == gtk.keysyms.Down:
            date = date + datetime.timedelta(days=1)
        elif (event.keyval == gtk.keysyms.Return or
              event.keyval == gtk.keysyms.KP_Enter):
            enter_pressed = True
        elif (event.keyval == gtk.keysyms.Escape):
            self.calendar_window.hide()
        else:
            return False
        
        if enter_pressed:
            self.prev_cal_day = "borken"
        else:
            self.prev_cal_day = date.day #prev_cal_day is our only way of checking that date is right
        
        self.date_calendar.select_month(date.month, date.year)
        self.date_calendar.select_day(date.day)
        return True
    
    def format_time(self, time):
        if not time:
            return ""
        
        #return time.strftime("%I:%M%p").lstrip("0").lower()
        return time.strftime("%H:%M").lower()
    
    def set_time(self, time_text):
        #convert forth and back so we have text formated as we want
        time = self.figure_time(time_text)
        time_text = self.format_time(time) 
        
        widget = None
        if self.get_widget("start_time").is_focus():
            widget = self.get_widget("start_time")
            self.get_widget("end_time") \
                .set_text(self.format_time(time + datetime.timedelta(minutes=30))) #set also end time on start time change


        elif self.get_widget("end_time").is_focus():
            start_datetime = self._get_datetime("start")
            start_time = self.figure_time(self.get_widget("start_time").get_text())
            delta = abs(time - start_time)

            end_date = start_datetime + delta
            self.get_widget("end_date").set_text(self.format_date(end_date))

            widget = self.get_widget("end_time")

        if widget:
            widget.set_text(time_text)

        widget.set_position(len(time_text))
        self.time_window.hide()        
        self.validate_fields()
        

    
    def on_time_tree_button_press_event(self, tree, event):
        model, iter = tree.get_selection().get_selected()
        time = model.get_value(iter, 0)
        self.set_time(time)
        
        
    def on_time_key_press_event(self, entry, event):
        if not self.time_tree.get_cursor():
            return
        
        i = self.time_tree.get_cursor()[0][0]

        if event.keyval == gtk.keysyms.Up:
            i-=1
        elif event.keyval == gtk.keysyms.Down:
            i+=1
        elif (event.keyval == gtk.keysyms.Return or
              event.keyval == gtk.keysyms.KP_Enter):
            
            self.set_time(self.time_tree.get_model()[i][0])
        elif (event.keyval == gtk.keysyms.Escape):
            self.time_window.hide()
        else:
            return False
        
        # keep it in the sane borders
        i = min(max(i, 0), len(self.time_tree.get_model()) - 1)
        
        self.time_tree.set_cursor(i)
        self.time_tree.scroll_to_cell(i, use_align = True, row_align = 0.4)
        return True
        
        
    def on_cancel_clicked(self, button):
        self.window.destroy()
        
    def on_activity_combo_changed(self, combo):
        self.validate_fields()

    def validate_fields(self):
        # do not allow empty tasks

        activity_text = self.get_widget("activity_text").get_text()
        start_time = self._get_datetime("start")

        end_time = self._get_datetime("end")
        if self.get_widget("in_progress").get_active():
            end_time = datetime.datetime.now()

        if start_time:
            self.draw_preview(start_time.date(), [start_time, end_time])


        
        looks_good = False
        if activity_text != "" and start_time and end_time and \
           (end_time - start_time).days == 0:
            looks_good = True

        self.get_widget("save_button").set_sensitive(looks_good)

    def on_window_key_pressed(self, tree, event_key):
        if (event_key.keyval == gtk.keysyms.Escape
          or (event_key.keyval == gtk.keysyms.w 
              and event_key.state & gtk.gdk.CONTROL_MASK)):
            
            if self.calendar_window.get_property("visible") or \
               self.time_window.get_property("visible"):
                return False
            
            self.window.destroy()


