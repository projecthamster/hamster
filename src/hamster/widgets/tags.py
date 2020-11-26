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

from gi.repository import GObject as gobject
from gi.repository import Gdk as gdk
from gi.repository import Gtk as gtk
from gi.repository import Pango as pango
import cairo
from math import pi

from hamster.lib import graphics, stuff
from hamster.lib.configuration import runtime

class TagsEntry(gtk.Entry):
    __gsignals__ = {
        'tags-selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, *, parent):
        gtk.Entry.__init__(self, parent=parent)
        self.ac_tags = None  # "autocomplete" tags
        self.filter = None # currently applied filter string
        self.filter_tags = [] #filtered tags

        self.popup = gtk.Window(type = gtk.WindowType.POPUP)
        self.popup.set_attached_to(self)
        self.popup.set_transient_for(self.get_ancestor(gtk.Window))

        self.scroll_box = gtk.ScrolledWindow()
        self.scroll_box.set_shadow_type(gtk.ShadowType.IN)
        self.scroll_box.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.ShadowType.NONE)

        self.tag_box = TagBox()
        self.tag_box.connect("tag-selected", self.on_tag_selected)
        self.tag_box.connect("tag-unselected", self.on_tag_unselected)


        viewport.add(self.tag_box)
        self.scroll_box.add(viewport)
        self.popup.add(self.scroll_box)

        self.set_icon_from_icon_name(gtk.EntryIconPosition.SECONDARY, "go-down-symbolic")

        self.connect("icon-press", self._on_icon_press)
        self.connect("key-press-event", self._on_key_press_event)
        self.connect("focus-out-event", self._on_focus_out_event)

        self._parent_click_watcher = None # bit lame but works

        self.external_listeners = [
            (runtime.storage, runtime.storage.connect('tags-changed', self.refresh_ac_tags))
        ]
        self.show()
        self.populate_suggestions()
        self.connect("destroy", self.on_destroy)

    def on_destroy(self, window):
        for obj, handler in self.external_listeners:
            obj.disconnect(handler)
        self.popup.destroy()
        self.popup = None


    def refresh_ac_tags(self, event):
        self.ac_tags = None

    def get_tags(self):
        # splits the string by comma and filters out blanks
        return [tag.strip() for tag in self.get_text().split(",") if tag.strip()]

    def on_tag_selected(self, tag_box, tag):
        cursor_tag = self.get_cursor_tag()
        if cursor_tag and tag.lower().startswith(cursor_tag.lower()):
            self.replace_tag(cursor_tag, tag)
            tags = self.get_tags()
        else:
            tags = self.get_tags()
            tags.append(tag)

        self.tag_box.selected_tags = tags


        self.set_tags(tags)
        self.update_tagsline(add=True)

        self.populate_suggestions()
        self.show_popup()

    def on_tag_unselected(self, tag_box, tag):
        tags = self.get_tags()
        while tag in tags: #it could be that dear user is mocking us and entering same tag over and over again
            tags.remove(tag)

        self.tag_box.selected_tags = tags

        self.set_tags(tags)
        self.update_tagsline(add=True)

    def hide_popup(self):
        self.popup.hide()
        if self._parent_click_watcher and self.get_toplevel().handler_is_connected(self._parent_click_watcher):
            self.get_toplevel().disconnect(self._parent_click_watcher)
            self._parent_click_watcher = None

    def show_popup(self):
        if not self.filter_tags:
            self.popup.hide()
            return

        if not self._parent_click_watcher:
            self._parent_click_watcher = self.get_toplevel().connect("button-press-event", self._on_focus_out_event)

        alloc = self.get_allocation()
        _, x, y = self.get_parent_window().get_origin()

        self.popup.move(x + alloc.x,y + alloc.y + alloc.height)

        w = alloc.width

        height = self.tag_box.count_height(w)

        self.scroll_box.set_size_request(w, height)
        self.popup.resize(w, height)
        self.popup.show_all()

    def refresh_activities(self):
        # scratch activities and categories so that they get repopulated on demand
        self.activities = None
        self.categories = None

    def populate_suggestions(self):
        self.ac_tags = self.ac_tags or [tag["name"] for tag in
                                        runtime.storage.get_tags(only_autocomplete=True)]

        cursor_tag = self.get_cursor_tag()

        self.filter = cursor_tag

        entered_tags = self.get_tags()
        self.tag_box.selected_tags = entered_tags

        self.filter_tags = [tag for tag in self.ac_tags
                            if (tag or "").lower().startswith((self.filter or "").lower())]

        self.tag_box.draw(self.filter_tags)



    def _on_focus_out_event(self, widget, event):
        self.hide_popup()

    def _on_icon_press(self, entry, icon_pos, event):
        # otherwise Esc could not hide popup
        self.grab_focus()
        # toggle popup
        if self.popup.get_visible():
            # remove trailing comma if any
            self.update_tagsline(add=False)
            self.hide_popup()
        else:
            # add trailing comma
            self.update_tagsline(add=True)
            self.populate_suggestions()
            self.show_popup()

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

        self.set_tags(tags)
        self.set_position(len(self.get_text()))

    def set_tags(self, tags):
        self.tags = tags
        self.update_tagsline()

    def update_tagsline(self, add=False):
        """Update tags line text.

        If add is True, prepare to add tags to the list:
        a comma is appended and the popup is displayed.
        """
        text = ", ".join(self.tags)
        if add and text:
            text = "{}, ".format(text)
        self.set_text(text)
        self.set_position(len(self.get_text()))

    def _on_key_press_event(self, entry, event):
        if event.keyval == gdk.KEY_Tab:
            if self.popup.get_property("visible"):
                #we have to replace
                if self.get_text() and self.get_cursor_tag() != self.filter_tags[0]:
                    self.replace_tag(self.get_cursor_tag(), self.filter_tags[0])
                    return True
                else:
                    return False
            else:
                return False

        elif event.keyval in (gdk.KEY_Return, gdk.KEY_KP_Enter):
            if self.popup.get_property("visible"):
                if self.get_text():
                    self.hide_popup()
                return True
            else:
                if self.get_text():
                    self.emit("tags-selected")
                return False

        elif event.keyval == gdk.KEY_Escape:
            if self.popup.get_property("visible"):
                self.hide_popup()
                return True
            else:
                return False

        else:
            self.populate_suggestions()
            self.show_popup()

        return False


class TagBox(graphics.Scene):
    __gsignals__ = {
        'tag-selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,)),
        'tag-unselected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,)),
    }

    def __init__(self, interactive = True):
        graphics.Scene.__init__(self)
        self.interactive = interactive
        self.hover_tag = None
        self.tags = []
        self.selected_tags = []
        self.layout = None

        if self.interactive:
            self.connect("on-mouse-over", self.on_mouse_over)
            self.connect("on-mouse-out", self.on_mouse_out)
            self.connect("on-click", self.on_tag_click)

        self.connect("on-enter-frame", self.on_enter_frame)

    def on_mouse_over(self, area, tag):
        tag.color = tag.graphics.colors.darker(tag.color, -20)

    def on_mouse_out(self, area, tag):
        if tag.text in self.selected_tags:
            tag.color = (242, 229, 97)
        else:
            tag.color = (241, 234, 170)


    def on_tag_click(self, area, event, tag):
        if not tag: return

        if tag.text in self.selected_tags:
            self.emit("tag-unselected", tag.text)
        else:
            self.emit("tag-selected", tag.text)
        self.on_mouse_out(area, tag) #paint
        self.redraw()

    def draw(self, tags):
        new_tags = []
        for label in tags:
            tag = Tag(label)
            if label in self.selected_tags:
                tag.color = (242, 229, 97)
            new_tags.append(tag)

        for tag in self.tags:
            self.sprites.remove(tag)

        self.add_child(*new_tags)
        self.tags = new_tags

        self.show()
        self.redraw()

    def count_height(self, width):
        # reposition tags and see how much space we take up
        self.width = width
        w, h = self.on_enter_frame(None, None)
        return h + 6

    def on_enter_frame(self, scene, context):
        cur_x, cur_y = 4, 4
        tag = None
        for tag in self.tags:
            if cur_x + tag.width >= self.width - 5:  #if we do not fit, we wrap
                cur_x = 5
                cur_y += tag.height + 6

            tag.x = cur_x
            tag.y = cur_y

            cur_x += tag.width + 6 #some padding too, please

        if tag:
            cur_y += tag.height + 2 # the last one

        return cur_x, cur_y

class Tag(graphics.Sprite):
    def __init__(self, text, interactive = True, color = "#F1EAAA"):
        graphics.Sprite.__init__(self, interactive = interactive)

        self.width, self.height = 0,0

        font = gtk.Style().font_desc
        font_size = int(font.get_size() * 0.8 / pango.SCALE) # 80% of default

        self.label = graphics.Label(text, size = font_size, color = (30, 30, 30), y = 1)
        self.color = color
        self.add_child(self.label)

        self.corner = int((self.label.height + 3) / 3) + 0.5
        self.label.x = self.corner + 6

        self.text = stuff.escape_pango(text)
        self.connect("on-render", self.on_render)

    def __setattr__(self, name, value):
        graphics.Sprite.__setattr__(self, name, value)
        if name == 'text' and hasattr(self, 'label'):
            self.label.text = value
            self.__dict__['width'], self.__dict__['height'] = int(self.label.x + self.label.width + self.label.height * 0.3), self.label.height + 3

    def on_render(self, sprite):
        self.graphics.set_line_style(width=1)

        self.graphics.move_to(0.5, self.corner)
        self.graphics.line_to([(self.corner, 0.5),
                               (self.width + 0.5, 0.5),
                               (self.width + 0.5, self.height - 0.5),
                               (self.corner, self.height - 0.5),
                               (0.5, self.height - self.corner)])
        self.graphics.close_path()
        self.graphics.fill_stroke(self.color, "#b4b4b4")

        self.graphics.circle(6, self.height / 2, 2)
        self.graphics.fill_stroke("#fff", "#b4b4b4")
