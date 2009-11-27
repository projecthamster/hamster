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

        self.font_size = 8
        self.mouse_regions = [] #regions of drawing that respond to hovering/clicking

        self.context, self.layout = None, None
        self.width, self.height = None, None
        self.__prev_mouse_regions = None
        
        self.tweener = pytweener.Tweener(0.4, pytweener.Easing.Cubic.easeInOut)
        self.framerate = 30 #thirty seems to be good enough to avoid flicker
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
        self.window.process_updates(True)

        self.last_frame_time = dt.datetime.now()

        return self.__animating


    def animate(self, object, params = {}, duration = None, easing = None, callback = None):
        if duration: params["tweenTime"] = duration  # if none will fallback to tweener's default
        if easing: params["tweenType"] = easing    # if none will fallback to tweener's default
        if callback: params["onCompleteFunction"] = callback
        self.tweener.addTween(object, **params)
        self.redraw_canvas()
    

    """ drawing on canvas bits """
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
class SimpleAnimation(Area):
    def __init__(self):
        Area.__init__(self)
        self.rect_x, self.rect_y = 10.5, 10.5
        self.rect_width, self.rect_height = 50, 50
        
    def on_expose(self):
        # on expose is called when we are ready to draw
        
        # fill_area is just a shortcut function
        # feel free to use self.context. move_to, line_to and others
        self.fill_area(self.rect_x,
                            self.rect_y,
                            self.rect_width,
                            self.rect_height, (168, 186, 136))

class BasicWindow:
    # close the window and quit
    def delete_event(self, widget, event, data=None):
        gtk.main_quit()
        return False

    def __init__(self):
        # Create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    
        self.window.set_title("Graphics Module")
        self.window.set_size_request(500, 500)
        self.window.connect("delete_event", self.delete_event)
    
        self.graphic = SimpleAnimation()
        
        box = gtk.VBox()
        box.pack_start(self.graphic)
        
        button = gtk.Button("Hello")
        button.connect("clicked", self.on_go_clicked)

        box.add_with_properties(button, "expand", False)
    
        self.window.add(box)
        self.window.show_all()


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
    