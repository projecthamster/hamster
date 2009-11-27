import time, datetime as dt
import gtk, gobject

import pango, cairo

class Colors(object):
    aluminium = [(238, 238, 236), (211, 215, 207), (186, 189, 182),
                 (136, 138, 133), (85, 87, 83), (46, 52, 54)]
    almost_white = (250, 250, 250)

    @staticmethod
    def normalize_rgb(color):
        # turns your average rgb into values with components in range 0..1
        # if none of the componets are over 1 - will return what it got
        if color[0] > 1 or color[1] > 0 or color[2] > 0:
            color = [c / 255.0 for c in color]
        return color
    
    @staticmethod
    def rgb(color):
        #return color that has each component in 0..255 range
        return [c*255 for c in Colors.normalize_rgb(color)]
        

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


        self.context = None
        self.layout = None
        self.width = None
        self.height = None
        self.value_boundaries = None #x_min, x_max, y_min, y_max
        
        self.x_factor, self.y_factor = None, None
        
        self.font_size = 8

        # use these to mark area where the "real" drawing is going on
        self.graph_x, self.graph_y = 0, 0
        self.graph_width, self.graph_height = None, None
        
        self.mouse_regions = [] #regions of drawing that respond to hovering/clicking
        self.__prev_mouse_regions = None


    def __rectangle(self, x, y, w, h, color, opacity = 0):
        if color[0] > 1: color = [c / 256.0 for c in color]

        if opacity:
            self.context.set_source_rgba(color[0], color[1], color[2], opacity)
        elif len(color) == 3:
            self.context.set_source_rgb(*color)
        else:
            self.context.set_source_rgba(*color)
            
        self.context.rectangle(x, y, w, h)
    
    def fill_area(self, x, y, w, h, color, opacity = 0):
        self.context.save()
        self.__rectangle(x, y, w, h, color, opacity)
        self.context.fill()
        self.context.restore()
        
    def fill_rectangle(self, x, y, w, h, color, opacity = 0):
        self.context.save()
        self.__rectangle(x, y, w, h, color, opacity)
        self.context.fill_preserve()
        self.set_color(color)
        self.context.stroke()
        self.context.restore()

    def set_text(self, text):
        # sets text and returns width and height of the layout
        self.layout.set_text(text)
        return self.layout.get_pixel_size()
        
    def set_color(self, color, opacity = None):
        color = Colors.normalize_rgb(color)

        if opacity:
            self.context.set_source_rgba(color[0], color[1], color[2], opacity)
        elif len(color) == 3:
            self.context.set_source_rgb(*color)
        else:
            self.context.set_source_rgba(*color)


    def register_mouse_region(self, x1, y1, x2, y2, region_name):
        self.mouse_regions.append((x1, y1, x2, y2, region_name))

    def redraw_canvas(self):
        """Force graph redraw"""
        if self.window:    #this can get called before expose
            self.queue_draw()
            self.window.process_updates(True)


    def _render(self):
        raise NotImplementedError


    """ exposure events """
    def do_configure_event(self, event):
        (self.__width, self.__height) = self.window.get_size()
        self.queue_draw()
                    
    def do_expose_event(self, event):
        self.width, self.height = self.window.get_size()
        self.context = self.window.cairo_create()


        self.context.set_antialias(cairo.ANTIALIAS_NONE)
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
        self._render()


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

 
