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
import math
import time, datetime as dt
import gtk, gobject

import pango, cairo

import pytweener
from pytweener import Easing

class Colors(object):
    aluminium = [(238, 238, 236), (211, 215, 207), (186, 189, 182),
                 (136, 138, 133), (85, 87, 83), (46, 52, 54)]
    almost_white = (250, 250, 250)

    @staticmethod
    def color(color):
        #parse color into rgb values
        if isinstance(color, str) or isinstance(color, unicode):
            color = gtk.gdk.Color(color)

        if isinstance(color, gtk.gdk.Color):
            color = [color.red / 65535.0, color.green / 65535.0, color.blue / 65535.0]
        else:
            # otherwise we assume we have color components in 0..255 range
            if color[0] > 1 or color[1] > 1 or color[2] > 1:
                color = [c / 255.0 for c in color]

        return color
    
    @staticmethod
    def rgb(color):
        return [c * 255 for c in Colors.color(color)]

class Area(gtk.DrawingArea):
    """Abstraction on top of DrawingArea to work specifically with cairo"""
    __gsignals__ = {
        "expose-event": "override",
        "configure_event": "override",
        "mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "button-release": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
    }

    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.set_events(gtk.gdk.EXPOSURE_MASK
                        | gtk.gdk.LEAVE_NOTIFY_MASK
                        | gtk.gdk.BUTTON_PRESS_MASK
                        | gtk.gdk.BUTTON_RELEASE_MASK
                        | gtk.gdk.POINTER_MOTION_MASK
                        | gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.connect("button_release_event", self.__on_button_release)
        self.connect("motion_notify_event", self.__on_mouse_move)
        self.connect("leave_notify_event", self.__on_mouse_out)

        self.font_size = 8
        self.mouse_regions = [] #regions of drawing that respond to hovering/clicking

        self.context, self.layout = None, None
        self.width, self.height = None, None
        self.__prev_mouse_regions = None
        
        self.tweener = pytweener.Tweener(0.4, pytweener.Easing.Cubic.easeInOut)
        self.framerate = 80
        self.last_frame_time = None
        self.__animating = False

    def on_expose(self):
        """ on_expose event is where you hook in all your drawing
            canvas has been initialized for you """
        raise NotImplementedError

    def redraw_canvas(self):
        """Redraw canvas. Triggers also to do all animations"""
        if not self.__animating: #if we are moving, then there is a timeout somewhere already
            self.__animating = True
            self.last_frame_time = dt.datetime.now()
            gobject.timeout_add(1000 / self.framerate, self.__interpolate)
            
    """ animation bits """
    def __interpolate(self):
        self.__animating = self.tweener.hasTweens()

        if not self.window: #will wait until window comes
            return self.__animating
        
        
        time_since_start = (dt.datetime.now() - self.last_frame_time).microseconds / 1000000.0
        self.tweener.update(time_since_start)

        self.queue_draw()

        self.last_frame_time = dt.datetime.now()
        return self.__animating


    def animate(self, object, params = {}, duration = None, easing = None, callback = None):
        if duration: params["tweenTime"] = duration  # if none will fallback to tweener default
        if easing: params["tweenType"] = easing    # if none will fallback to tweener default
        if callback: params["onCompleteFunction"] = callback
        self.tweener.addTween(object, **params)
        self.redraw_canvas()
    

    """ drawing on canvas bits """
    def draw_rect(self, x, y, w, h, corner_radius = 0):
        if corner_radius <=0:
            self.context.rectangle(x, y, w, h)
            return

        # make sure that w + h are larger than 2 * corner_radius
        corner_radius = min(corner_radius, min(w, h) / 2)

        x2, y2 = x + w, y + h

        half_corner = corner_radius / 2
        
        self.context.move_to(x + corner_radius, y);
        self.context.line_to(x2 - corner_radius, y);
        # top-right
        self.context.curve_to(x2 - half_corner, y,
                              x2, y + half_corner,
                              x2, y + corner_radius)

        self.context.line_to(x2, y2 - corner_radius);
        # bottom-right
        self.context.curve_to(x2, y2 - half_corner,
                              x2 - half_corner, y+h,
                              x2 - corner_radius,y+h)

        self.context.line_to(x + corner_radius, y2);
        # bottom-left
        self.context.curve_to(x + half_corner, y2,
                              x, y2 - half_corner,
                              x,y2 - corner_radius)

        self.context.line_to(x, y + corner_radius);
        # top-left
        self.context.curve_to(x, y + half_corner,
                              x + half_corner, y,
                              x + corner_radius,y)


    def rectangle(self, x, y, w, h, color = None, opacity = 0):
        if color:
            self.set_color(color, opacity)
        self.context.rectangle(x, y, w, h)
    
    def fill_area(self, x, y, w, h, color, opacity = 0):
        self.rectangle(x, y, w, h, color, opacity)
        self.context.fill()

    def set_text(self, text):
        # sets text and returns width and height of the layout
        self.layout.set_text(text)
        return self.layout.get_pixel_size()
        
    def set_color(self, color, opacity = None):
        color = Colors.color(color) #parse whatever we have there into a normalized triplet

        if opacity:
            self.context.set_source_rgba(color[0], color[1], color[2], opacity)
        elif len(color) == 3:
            self.context.set_source_rgb(*color)
        else:
            self.context.set_source_rgba(*color)


    def register_mouse_region(self, x1, y1, x2, y2, region_name):
        self.mouse_regions.append((x1, y1, x2, y2, region_name))

    """ exposure events """
    def do_configure_event(self, event):
        (self.width, self.height) = self.window.get_size()

    def do_expose_event(self, event):
        self.width, self.height = self.window.get_size()
        self.context = self.window.cairo_create()

        self.context.rectangle(event.area.x, event.area.y,
                               event.area.width, event.area.height)
        self.context.clip()

        self.layout = self.context.create_layout()
        default_font = pango.FontDescription(gtk.Style().font_desc.to_string())
        default_font.set_size(self.font_size * pango.SCALE)
        self.layout.set_font_description(default_font)
        alloc = self.get_allocation()  #x, y, width, height
        self.width, self.height = alloc.width, alloc.height
        
        self.mouse_regions = [] #reset since these can move in each redraw
        self.on_expose()


    """ mouse events """
    def __on_mouse_move(self, area, event):
        if not self.mouse_regions:
            return

        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state
        
        mouse_regions = []
        for region in self.mouse_regions:
            if region[0] < x < region[2] and region[1] < y < region[3]:
                mouse_regions.append(region[4])
        
        if mouse_regions:
            area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))
        else:
            area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.ARROW))

        if mouse_regions != self.__prev_mouse_regions:
            self.emit("mouse-over", mouse_regions)

        self.__prev_mouse_regions = mouse_regions

    def __on_mouse_out(self, area, event):
        self.__prev_mouse_regions = None
        self.emit("mouse-over", [])

    def __on_button_release(self, area, event):
        if not self.mouse_regions:
            return

        x = event.x
        y = event.y
        state = event.state
        
        mouse_regions = []
        for region in self.mouse_regions:
            if region[0] < x < region[2] and region[1] < y < region[3]:
                mouse_regions.append(region[4])

        if mouse_regions:
            self.emit("button-release", mouse_regions)

 


""" simple example """
class SampleArea(Area):
    def __init__(self):
        Area.__init__(self)
        self.rect_x, self.rect_y = 100, -100
        self.rect_width, self.rect_height = 90, 90

        self.text_y = -100
        
        
    def on_expose(self):
        # on expose is called when we are ready to draw
        
        # fill_area is just a shortcut function
        # feel free to use self.context. move_to, line_to and others
        self.font_size = 32
        self.layout.set_text("Hello, World!")
        
        self.draw_rect(round(self.rect_x),
                       round(self.rect_y),
                       self.rect_width,
                       self.rect_height,
                       10)
        
        self.set_color("#ff00ff")
        self.context.fill()

        self.context.move_to((self.width - self.layout.get_pixel_size()[0]) / 2,
                             self.text_y)
        
        self.set_color("#333")
        self.context.show_layout(self.layout)
        

class BasicWindow:
    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title("Graphics Module")
        window.set_size_request(300, 300)
        window.connect("delete_event", lambda *args: gtk.main_quit())
    
        self.graphic = SampleArea()
        
        box = gtk.VBox()
        box.pack_start(self.graphic)
        
        button = gtk.Button("Hello")
        button.connect("clicked", self.on_go_clicked)

        box.add_with_properties(button, "expand", False)
    
        window.add(box)
        window.show_all()
        
        # drop the hello on init
        self.graphic.animate(self.graphic,
                            dict(text_y = 120),
                            duration = 0.7,
                            easing = Easing.Bounce.easeOut)


    def on_go_clicked(self, widget):
        import random
        
        # set x and y to random position within the drawing area
        x = round(min(random.random() * self.graphic.width,
                      self.graphic.width - self.graphic.rect_width))
        y = round(min(random.random() * self.graphic.height,
                      self.graphic.height - self.graphic.rect_height))
        
        # here we call the animate function with parameters we would like to change
        # the easing functions outside graphics module can be accessed via
        # graphics.Easing
        self.graphic.animate(self.graphic,
                             dict(rect_x = x, rect_y = y),
                             duration = 0.8,
                             easing = Easing.Elastic.easeOut)


if __name__ == "__main__":
   example = BasicWindow()
   gtk.main()
    