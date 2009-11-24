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

import gtk, gobject
import pango, cairo
from math import pi

from hamster import graphics

from hamster.configuration import runtime

class TagsEntry(gtk.Entry):
    __gsignals__ = {
        'tags-selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self):
        gtk.Entry.__init__(self)
        self.tags = None
        self.filter = None # currently applied filter string
        self.filter_tags = [] #filtered tags
        
        self.popup = gtk.Window(type = gtk.WINDOW_POPUP)
        self.scroll_box = gtk.ScrolledWindow()
        self.scroll_box.set_shadow_type(gtk.SHADOW_IN)
        self.scroll_box.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_NONE)
        
        self.tag_box = TagBox()
        self.tag_box.connect("tag-selected", self.on_tag_selected)
        self.tag_box.connect("tag-unselected", self.on_tag_unselected)

        
        viewport.add(self.tag_box)
        self.scroll_box.add(viewport)
        self.popup.add(self.scroll_box)
        
        self.connect("button-press-event", self._on_button_press_event)
        self.connect("key-press-event", self._on_key_press_event)
        self.connect("key-release-event", self._on_key_release_event)
        self.connect("focus-out-event", self._on_focus_out_event)

        runtime.dispatcher.add_handler('new_tags_added', self.refresh_tags)
        self.show()
        self.populate_suggestions()

    def refresh_tags(self, event, data):
        self.tags = None

    def get_tags(self):
        # splits the string by comma and filters out blanks
        return [tag.strip() for tag in self.get_text().split(",") if tag.strip()]

    def on_tag_selected(self, tag_box, tag):
        tags = self.get_tags()
        tags.append(tag)

        self.set_text(", ".join(tags))
        self.set_position(len(self.get_text()))

    def on_tag_unselected(self, tag_box, tag):
        tags = self.get_tags()
        print tags
        while tag in tags: #it could be that dear user is mocking us and entering same tag over and over again
            tags.remove(tag)
            
        print tags

        self.set_text(", ".join(tags))
        self.set_position(len(self.get_text()))
        
        
    def hide_popup(self):
        self.popup.hide()

    def show_popup(self):
        if not self.filter_tags:
            self.popup.hide()
            return
        
        alloc = self.get_allocation()
        x, y = self.get_parent_window().get_origin()

        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)

        w = alloc.width
        

        self.popup.show_all()
        self.scroll_box.set_size_request(w, self.tag_box.count_height())
        self.popup.resize(w, self.tag_box.count_height())

        
    def complete_inline(self):
        return         

    def refresh_activities(self):
        # scratch activities and categories so that they get repopulated on demand
        self.activities = None
        self.categories = None

    def populate_suggestions(self):
        self.tags = self.tags or [tag["name"] for tag in runtime.storage.get_tags(autocomplete = True)]

        cursor_tag = self.get_cursor_tag()
            
        self.filter = cursor_tag

        entered_tags = self.get_tags()
        self.tag_box.selected_tags = entered_tags
        
        self.filter_tags = [tag for tag in self.tags if tag.startswith(self.filter)]
        
        self.tag_box.draw(self.filter_tags)
        
        

    def _on_focus_out_event(self, widget, event):
        self.hide_popup()

    def _on_button_press_event(self, button, event):
        self.populate_suggestions()
        self.show_popup()

    def _on_key_release_event(self, entry, event):
        if (event.keyval in (gtk.keysyms.Return, gtk.keysyms.KP_Enter)):
            if self.popup.get_property("visible"):
                self.hide_popup()
                return True
            else:
                self.emit("tags-selected")
                return False
        elif (event.keyval == gtk.keysyms.Escape):
            if self.popup.get_property("visible"):
                self.hide_popup()
                return True
            else:
                return False
        else:
            self.populate_suggestions()
            self.show_popup()
            
            if event.keyval not in (gtk.keysyms.Delete, gtk.keysyms.BackSpace):
                self.complete_inline()

    
    def get_cursor_tag(self):
        #returns the tag on which the cursor is on right now
        if self.get_selection_bounds():
            cursor = self.get_selection_bounds()[0]
        else:
            cursor = self.get_position()

        text = self.get_text()

        return text[text.rfind(",", 0, cursor)+1:max(text.find(",", cursor+1)+1, len(text))].strip()


    def replace_tag(self, old_tag, new_tag):
        tags = self.get_tags()
        if old_tag in tags:
            tags[tags.index(old_tag)] = new_tag

        if self.get_selection_bounds():
            cursor = self.get_selection_bounds()[0]
        else:
            cursor = self.get_position()
        
        self.set_text(", ".join(tags))
        self.set_position(cursor + len(new_tag)-len(old_tag)) # put the cursor back

    def _on_key_press_event(self, entry, event):
        if event.keyval == gtk.keysyms.Tab:
            if self.popup.get_property("visible"):
                #we have to replace
                if self.get_text() and self.get_cursor_tag() != self.filter_tags[0]:
                    self.replace_tag(self.get_cursor_tag(), self.filter_tags[0])
                    return True
                else:
                    return False
            else:
                return False

        return False


class TagBox(graphics.Area):
    __gsignals__ = {
        'tag-selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,)),
        'tag-unselected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,)),
    }

    def __init__(self):
        graphics.Area.__init__(self)
        self.font_size = 10
        self.connect("mouse-over", self.on_tag_hover)
        self.connect("button-release", self.on_tag_click)
        self.hover_tag = None
        self.tags = []
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
            self.emit("tag-unselected", tag)
        else:
            self.selected_tags.append(tag)
            self.emit("tag-selected", tag)

        self.redraw_canvas()
        
    def draw(self, tags):
        """Draw chart with given data"""
        self.tags = tags
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
        

    def count_height(self):
        if not self.width:
            return 120
        
        # tells you how much height in this width is needed to show all tags
        if not self.tags:
            return None
        
        cur_x, cur_y = 4, 4
        for tag in self.tags:
            w, h = self.tag_size(tag)
            if cur_x + w >= self.width - 5:  #if we don't fit, we wrap
                cur_x = 5
                cur_y += h + 6
            
            cur_x += w + 8 #some padding too, please
        
        cur_y = cur_y + h + 6
        
        return cur_y

    
    def _render(self):
        self.fill_area(0, 0, self.width, self.height, (255,255,255))

        cur_x, cur_y = 4, 4
        for tag in self.tags:
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
