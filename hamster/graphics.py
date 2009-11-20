import time, datetime as dt
import gtk, gobject

import pango, cairo

class Colors(object):
    aluminium = [(238, 238, 236), (211, 215, 207), (186, 189, 182),
                 (136, 138, 133), (85, 87, 83), (46, 52, 54)]
    almost_white = (250, 250, 250)

class Area(gtk.DrawingArea):
    """Abstraction on top of DrawingArea to work specifically with cairo"""
    __gsignals__ = {
        "expose-event": "override",
        "configure_event": "override",
        "mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "button-release": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
    }

    def do_configure_event ( self, event ):
        (self.__width, self.__height) = self.window.get_size()
        self.queue_draw()
                    
    def do_expose_event ( self, event ):
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

    def set_text(self, text):
        # sets text and returns width and height of the layout
        self.layout.set_text(text)
        w, h = self.layout.get_pixel_size()
        return w, h
        
        
    def set_color(self, color, opacity = None):
        if color[0] > 1 or color[1] > 0 or color[2] > 0:
            color = [c / 255.0 for c in color]

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

    def set_value_range(self, x_min = None, x_max = None, y_min = None, y_max = None):
        """sets up our internal conversion matrix, because cairo one will
        scale also fonts and we need something in between!"""
        
        #store given params, we might redo the math later
        if not self.value_boundaries:
            self.value_boundaries = [x_min, x_max, y_min, y_max]
        else:
            if x_min != None:
                self.value_boundaries[0] = x_min
            if x_max != None:
                self.value_boundaries[1] = x_max
            if y_min != None:
                self.value_boundaries[2] = y_min
            if y_max != None:
                self.value_boundaries[3] = y_max 
        self.x_factor, self.y_factor = None, None
        self._get_factors()

    def _get_factors(self):
        if not self.x_factor:
            self.x_factor = 1
            if self.value_boundaries and self.value_boundaries[0] != None and self.value_boundaries[1] != None:
                self.x_factor = float(self.graph_width or self.width) / abs(self.value_boundaries[1] - self.value_boundaries[0])
                
        if not self.y_factor:            
            self.y_factor = 1
            if self.value_boundaries and self.value_boundaries[2] != None and self.value_boundaries[3] != None:
                self.y_factor = float(self.graph_height or self.height) / abs(self.value_boundaries[3] - self.value_boundaries[2])

        return self.x_factor, self.y_factor        


    def get_pixel(self, x_value = None, y_value = None):
        """returns screen pixel position for value x and y. Useful to
        get and then pad something

        x = min1 + (max1 - min1) * (x / abs(max2-min2))  
            => min1 + const1 * x / const2
            => const3 = const1 / const2
            => min + x * const3
        """
        x_factor, y_factor = self._get_factors()

        if x_value != None:
            if self.value_boundaries and self.value_boundaries[0] != None:
                if self.value_boundaries[1] > self.value_boundaries[0]:
                    x_value = self.value_boundaries[0] + x_value * x_factor
                else: #case when min is larger than max (flipped)
                    x_value = self.value_boundaries[1] - x_value * x_factor
            if y_value is None:
                return x_value + self.graph_x

        if y_value != None:
            if self.value_boundaries and self.value_boundaries[2] != None:
                if self.value_boundaries[3] > self.value_boundaries[2]:
                    y_value = self.value_boundaries[2] + y_value * y_factor
                else: #case when min is larger than max (flipped)
                    y_value = self.value_boundaries[2] - y_value * y_factor
            if x_value is None:
                return y_value + self.graph_y
            
        return x_value + self.graph_x, y_value + self.graph_y

    def get_value_at_pos(self, x = None, y = None):
        """returns mapped value at the coordinates x,y"""
        x_factor, y_factor = self._get_factors()
        
        if x != None:
            x = (x - self.graph_x)  / x_factor
            if y is None:
                return x
        if y != None:
            y = (y - self.graph_x) / y_factor
            if x is None:
                return y
        return x, y            
        
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
        self.context.fill()
        self.__rectangle(x, y, w, h, color, 0)
        self.context.stroke()
        self.context.restore()

    def longest_label(self, labels):
        """returns width of the longest label"""
        max_extent = 0
        for label in labels:
            self.layout.set_text(label)
            label_w, label_h = self.layout.get_pixel_size()
            max_extent = max(label_w + 5, max_extent)
        
        return max_extent
    
    def move_to(self, x, y):
        """our copy of moveto that takes into account our transformations"""
        self.context.move_to(*self.get_pixel(x, y))

    def line_to(self, x, y):
        self.context.line_to(*self.get_pixel(x, y))
        
    def __on_mouse_out(self, area, event):
        self.__prev_mouse_regions = None
        self.emit("mouse-over", [])

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


class Integrator(object):
    """an iterator, inspired by "visualizing data" book to simplify animation"""
    def __init__(self, start_value, damping = 0.5, attraction = 0.2):
        #if we got datetime, convert it to unix time, so we operate with numbers again
        self.current_value = start_value
        if isinstance(start_value, dt.datetime):
            self.current_value = int(time.mktime(start_value.timetuple()))
            
        self.value_type = type(start_value)

        self.target_value = start_value
        self.current_frame = 0

        self.targeting = False
        self.vel, self.accel, self.force = 0, 0, 0
        self.mass = 1
        self.damping = damping
        self.attraction = attraction

    def __repr__(self):
        current, target = self.current_value, self.target_value
        if self.value_type == dt.datetime:
            current = dt.datetime.fromtimestamp(current)
            target = dt.datetime.fromtimestamp(target)
        return "<Integrator %s, %s>" % (current, target)
        
    def target(self, value):
        """target next value"""
        self.targeting = True
        self.target_value = value
        if isinstance(value, dt.datetime):
            self.target_value = int(time.mktime(value.timetuple()))
        
    def update(self):
        """goes from current to target value
        if there is any action needed. returns velocity, which is synonym from
        delta. Use it to determine when animation is done (experiment to find
        value that fits you!"""

        if self.targeting:
            self.force += self.attraction * (self.target_value - self.current_value)

        self.accel = self.force / self.mass
        self.vel = (self.vel + self.accel) * self.damping
        self.current_value += self.vel    
        self.force = 0
        return abs(self.vel)

    def finish(self):
        self.current_value = self.target_value
    
    @property
    def value(self):
        if self.value_type == dt.datetime:
            return dt.datetime.fromtimestamp(self.current_value)
        else:
            return self.current_value
 
