# - coding: utf-8 -

# Copyright (C) 2008-2010 Toms Bauģis <toms.baugis at gmail.com>
# Dual licensed under the MIT or GPL Version 2 licenses.
# See http://github.com/tbaugis/hamster_experiments/blob/master/README.textile

import math
import datetime as dt
import gtk, gobject

import pango, cairo

try:
    import pytweener
except: # we can also live without tweener. Scene.animate won't work in this case
    pytweener = None

import colorsys
from collections import deque

class Colors(object):
    def parse(self, color):
        assert color is not None

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

    def rgb(self, color):
        return [c * 255 for c in self.parse(color)]

    def gdk(self, color):
        c = self.parse(color)
        return gtk.gdk.Color(c[0] * 65535.0, c[1] * 65535.0, c[2] * 65535.0)

    def is_light(self, color):
        # tells you if color is dark or light, so you can up or down the scale for improved contrast
        return colorsys.rgb_to_hls(*self.rgb(color))[1] > 150

    def darker(self, color, step):
        # returns color darker by step (where step is in range 0..255)
        hls = colorsys.rgb_to_hls(*self.rgb(color))
        return colorsys.hls_to_rgb(hls[0], hls[1] - step, hls[2])
Colors = Colors() # this is a static class, so an instance will do -- TODO - could be bad practice

class Graphics(object):
    """If context is given upon contruction, will perform drawing
       operations on context instantly. Otherwise queues up the drawing
       instructions and performs them in passed-in order when _draw is called
       with context.

       Most of instructions are mapped to cairo functions by the same name.
       Where there are differences, documenation is provided.

       See http://www.cairographics.org/documentation/pycairo/reference/context.html#class-context
       for detailed description of the cairo drawing functions.
    """
    def __init__(self, context = None):
        self._instructions = deque() # instruction set until it is converted into path-based instructions
        self.instructions = [] # paths colors and operations
        self.colors = Colors
        self.extents = None
        self.opacity = 1.0
        self.paths = None
        self.last_matrix = None
        self.context = context

    def clear(self):
        """clear all instructions"""
        self._instructions = deque()
        self.paths = []

    def _stroke(self, context): context.stroke()
    def stroke(self, color = None, alpha = 1):
        """stroke the line with given color and opacity"""
        if color or alpha < 1:self.set_color(color, alpha)
        self._add_instruction(self._stroke,)

    def _fill(self, context): context.fill()
    def fill(self, color = None, alpha = 1):
        """fill path with given color and opacity"""
        if color or alpha < 1:self.set_color(color, alpha)
        self._add_instruction(self._fill,)

    def _stroke_preserve(self, context): context.stroke_preserve()
    def stroke_preserve(self, color = None, alpha = 1):
        """same as stroke, only after stroking, don't discard the path"""
        if color or alpha < 1:self.set_color(color, alpha)
        self._add_instruction(self._stroke_preserve,)

    def _fill_preserve(self, context): context.fill_preserve()
    def fill_preserve(self, color = None, alpha = 1):
        """same as fill, only after filling, don't discard the path"""
        if color or alpha < 1:self.set_color(color, alpha)
        self._add_instruction(self._fill_preserve,)

    def _new_path(self, context): context.new_path()
    def new_path(self):
        """discard current path"""
        self._add_instruction(self._new_path,)

    def _paint(self, context): context.paint()
    def paint(self):
        """errrm. paint"""
        self._add_instruction(self._paint,)

    def _set_source_surface(self, context, image, x, y): context.set_source_surface(image, x, y)
    def set_source_surface(self, image, x = 0, y = 0): self._add_instruction(self._set_source_surface, image, x, y)

    def _move_to(self, context, x, y): context.move_to(x, y)
    def move_to(self, x, y):
        """change current position"""
        self._add_instruction(self._move_to, x, y)

    def _line_to(self, context, x, y): context.line_to(x, y)
    def line_to(self, x, y):
        """draw line"""
        self._add_instruction(self._line_to, x, y)

    def _curve_to(self, context, x, y, x2, y2, x3, y3): context.curve_to(x, y, x2, y2, x3, y3)
    def curve_to(self, x, y, x2, y2, x3, y3):
        """draw curve. (x2, y2) is the middle point of the curve"""
        self._add_instruction(self._curve_to, x, y, x2, y2, x3, y3)

    def _close_path(self, context): context.close_path()
    def close_path(self):
        """connect end with beginning of path"""
        self._add_instruction(self._close_path,)

    def _set_line_width(self, context, width):
        context.set_line_width(width)
    def set_line_style(self, width = None):
        """change the width of the line"""
        if width is not None:
            self._add_instruction(self._set_line_width, width)

    def _set_color(self, context, r, g, b, a):
        if a * self.opacity >= 1:
            context.set_source_rgb(r, g, b)
        else:
            context.set_source_rgba(r, g, b, a * self.opacity)

    def set_color(self, color, alpha = 1):
        """set active color. You can use hex colors like "#aaa", or you can use
        normalized RGB tripplets (where every value is in range 0..1), or
        you can do the same thing in range 0..65535"""
        color = self.colors.parse(color) #parse whatever we have there into a normalized triplet
        if len(color) == 4 and alpha is None:
            alpha = color[3]
        r, g, b = color[:3]
        self._add_instruction(self._set_color, r, g, b, alpha)

    def _arc(self, context, x, y, radius, start_angle, end_angle): context.arc(x, y, radius, start_angle, end_angle)
    def arc(self, x, y, radius, start_angle, end_angle):
        """draw arc going counter-clockwise from start_angle to end_angle"""
        self._add_instruction(self._arc, x, y, radius, start_angle, end_angle)

    def circle(self, x, y, radius):
        """draw circle"""
        self._add_instruction(self._arc, x, y, radius, 0, math.pi * 2)

    def ellipse(self, x, y, width, height, edges):
        """draw 'perfect' ellipse, opposed to squashed circle. works also for
           equilateral polygons"""
        steps = edges or max((32, width, height)) / 3 # the automatic edge case is somewhat arbitrary

        angle = 0
        step = math.pi * 2 / steps
        points = []
        while angle < math.pi * 2:
            points.append((self.width / 2.0 * math.cos(angle),
                           self.height / 2.0 * math.sin(angle)))
            angle += step

        min_x = min((point[0] for point in points))
        min_y = min((point[1] for point in points))

        self._move_to(points[0][0] - min_x, points[0][1] - min_y)
        for x, y in points:
            self._line_to(x - min_x, y - min_y)
        self._line_to(points[0][0] - min_x, points[0][1] - min_y)


    def _arc_negative(self, context, x, y, radius, start_angle, end_angle): context.arc_negative(x, y, radius, start_angle, end_angle)
    def arc_negative(self, x, y, radius, start_angle, end_angle):
        """draw arc going clockwise from start_angle to end_angle"""
        self._add_instruction(self._arc_negative, x, y, radius, start_angle, end_angle)

    def _rounded_rectangle(self, context, x, y, x2, y2, corner_radius):
        half_corner = corner_radius / 2

        context.move_to(x + corner_radius, y)
        context.line_to(x2 - corner_radius, y)
        context.curve_to(x2 - half_corner, y, x2, y + half_corner, x2, y + corner_radius)
        context.line_to(x2, y2 - corner_radius)
        context.curve_to(x2, y2 - half_corner, x2 - half_corner, y2, x2 - corner_radius,y2)
        context.line_to(x + corner_radius, y2)
        context.curve_to(x + half_corner, y2, x, y2 - half_corner, x, y2 - corner_radius)
        context.line_to(x, y + corner_radius)
        context.curve_to(x, y + half_corner, x + half_corner, y, x + corner_radius,y)

    def _rectangle(self, context, x, y, w, h): context.rectangle(x, y, w, h)
    def rectangle(self, x, y, width, height, corner_radius = 0):
        "draw a rectangle. if corner_radius is specified, will draw rounded corners"
        if corner_radius <=0:
            self._add_instruction(self._rectangle, x, y, width, height)
            return

        # make sure that w + h are larger than 2 * corner_radius
        corner_radius = min(corner_radius, min(width, height) / 2)
        x2, y2 = x + width, y + height
        self._add_instruction(self._rounded_rectangle, x, y, x2, y2, corner_radius)

    def fill_area(self, x, y, width, height, color, opacity = 1):
        """fill rectangular area with specified color"""
        self.rectangle(x, y, width, height)
        self.fill(color, opacity)


    def _show_layout(self, context, text, font_desc, alignment, width, wrap, ellipsize):
        layout = context.create_layout()
        layout.set_font_description(font_desc)
        layout.set_text(text)
        layout.set_width(width)
        layout.set_alignment(alignment)

        if width > 0:
            if wrap is not None:
                layout.set_wrap(wrap)
            else:
                layout.set_ellipsize(ellipsize or pango.ELLIPSIZE_END)

        context.show_layout(layout)

    def show_text(self, text):
        """display text with system's default font"""
        font_desc = pango.FontDescription(gtk.Style().font_desc.to_string())
        self.show_layout(text, font_desc)

    def show_layout(self, text, font_desc, alignment = pango.ALIGN_LEFT, width = -1, wrap = None, ellipsize = None):
        """display text. font_desc is string of pango font description
           often handier than calling this function directly, is to create
           a class:Label object
        """
        self._add_instruction(self._show_layout, text, font_desc, alignment, width, wrap, ellipsize)

    def _remember_path(self, context):
        context.save()
        context.identity_matrix()
        matrix = context.get_matrix()

        new_extents = context.path_extents()
        self.extents = self.extents or new_extents
        self.extents = (min(self.extents[0], new_extents[0]),
                        min(self.extents[1], new_extents[1]),
                        max(self.extents[2], new_extents[2]),
                        max(self.extents[3], new_extents[3]))

        self.paths.append(context.copy_path_flat())

        context.restore()


    def _add_instruction(self, function, *params):
        if self.context:
            function(self.context, *params)
        else:
            self.paths = None
            self._instructions.append((function, params))


    def _draw(self, context, with_extents = False):
        """draw accumulated instructions in context"""

        if self._instructions: #new stuff!
            self.instructions = deque()
            current_color = None
            current_line = None
            instruction_cache = []

            while self._instructions:
                instruction, args = self._instructions.popleft()

                if instruction in (self._set_source_surface, self._paint):
                    self.instructions.append((None, None, None, instruction, args))

                elif instruction == self._show_layout:
                    x,y = context.get_current_point() or (0,0)
                    self.instructions.append((None, None, None, self._move_to, (x,y))) #previous move_to call will be actually executed after this
                    self.instructions.append((None, current_color, None, instruction, args))

                else:
                    if instruction == self._set_color:
                        current_color = args

                    if instruction == self._set_line_width:
                        current_line = args

                    elif instruction in (self._stroke, self._fill, self._stroke_preserve, self._fill_preserve):
                        self.instructions.append((context.copy_path(), current_color, current_line, instruction, ()))
                        context.new_path() # reset even on preserve as the instruction will preserve it instead
                        instruction_cache = []
                    else:
                        instruction(context, *args)
                        instruction_cache.append((instruction, args))


                while instruction_cache: # stroke's missing so we just cache
                    instruction, args = instruction_cache.pop(0)
                    self.instructions.append((None, None, None, instruction, args))


        # if we have been moved around, we should update bounds
        check_extents = with_extents and (context.get_matrix() != self.last_matrix or not self.paths)
        if check_extents:
            self.paths = deque()
            self.extents = None

        for path, color, line, instruction, args in self.instructions:
            if color: self._set_color(context, *color)
            if line: self._set_line_width(context, *line)

            if path:
                context.append_path(path)
                if check_extents:
                    self._remember_path(context)

            if instruction:
                instruction(context, *args)

        self.last_matrix = context.get_matrix()



class Sprite(gtk.Object):
    """The Sprite class is a basic display list building block: a display list
       node that can display graphics and can also contain children.
       Once you have created the sprite, use Scene's add_child to add it to
       scene"""

    __gsignals__ = {
        "on-mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-mouse-out": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        #"on-draw": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }
    def __init__(self, x = 0, y = 0, opacity = 1, visible = True, rotation = 0, pivot_x = 0, pivot_y = 0, interactive = True, draggable = False):
        gtk.Widget.__init__(self)
        self.sprites = []
        self.graphics = Graphics()
        self.interactive = interactive
        self.draggable = draggable
        self.pivot_x, self.pivot_y = pivot_x, pivot_y # rotation point in sprite's coordinates
        self.opacity = opacity
        self.visible = visible
        self.parent = None
        self.x, self.y = x, y
        self.rotation = rotation

    def add_child(self, *sprites):
        """Add child sprite. Child will be nested within parent"""
        for sprite in sprites:
            self.sprites.append(sprite)
            sprite.parent = self

    def _draw(self, context, opacity = 1):
        if self.visible is False:
            return

        if self.x or self.y or self.rotation:
            context.save()

            if self.x or self.y or self.pivot_x or self.pivot_y:
                context.translate(self.x + self.pivot_x, self.y + self.pivot_y)

            if self.rotation:
                context.rotate(self.rotation)

            if self.pivot_x or self.pivot_y:
                context.translate(-self.pivot_x, -self.pivot_y)

        self.graphics.opacity = self.opacity * opacity

        #self.emit("on-draw") # TODO - this is expensive when doing constant redraw with many frames. maybe we can have a simple callback here?
        self.graphics._draw(context, self.interactive or self.draggable)

        for sprite in self.sprites:
            sprite._draw(context, self.opacity * opacity)

        if self.x or self.y or self.rotation:
            context.restore()

    def _on_click(self, button_state):
        self.emit("on-click", button_state)

    def _on_mouse_over(self):
        # scene will call us when there is mouse
        self.emit("on-mouse-over")

    def _on_mouse_out(self):
        # scene will call us when there is mouse
        self.emit("on-mouse-out")

    def _on_drag(self, x, y):
        # scene will call us when there is mouse
        self.emit("on-drag", (x, y))


"""a few shapes"""

class Shape(Sprite):
    """shape is a simple continuous shape that can have fill and stroke"""
    def __init__(self, stroke = None, fill = None, line_width = None, **kwargs):
        kwargs.setdefault("interactive", False)
        Sprite.__init__(self, **kwargs)
        self.stroke = stroke # stroke color
        self.fill = fill     # fill color
        self.line_width = line_width
        self._sprite_dirty = True # a dirty shape needs it's graphics regenerated, because params have changed

    def __setattr__(self, name, val):
        self.__dict__[name] = val
        if name not in ('_sprite_dirty', 'x', 'y', 'rotation'):
            self._sprite_dirty = True


    def _draw(self, *args, **kwargs):
        if self._sprite_dirty:
            self.graphics.clear()
            self.draw_shape()
            self._color()
            self._sprite_dirty = False

        Sprite._draw(self, *args,  **kwargs)


    def draw_shape(self):
        """implement this function in your subclassed object. leave out stroke
        and fill instructions - those will be performed by the shape itself, using
        the stroke and fill attributes"""
        raise(NotImplementedError, "expected draw_shape functoin in the class")

    def _color(self):
        if self.line_width:
            self.graphics.set_line_style(self.line_width)

        if self.fill:
            if self.stroke:
                self.graphics.fill_preserve(self.fill)
            else:
                self.graphics.fill(self.fill)

        if self.stroke:
            self.graphics.stroke(self.stroke)


class Label(Shape):
    def __init__(self, text = "", size = 10, color = None, alignment = pango.ALIGN_LEFT, **kwargs):
        kwargs.setdefault('interactive', False)
        Shape.__init__(self, **kwargs)
        self.width, self.height = None, None

        self._bounds_width = -1
        self.wrap = None      # can be set to pango. [WRAP_WORD, WRAP_CHAR, WRAP_WORD_CHAR]
        self.ellipsize = None # can be set to pango. [ELLIPSIZE_NONE, ELLIPSIZE_START, ELLIPSIZE_MIDDLE, ELLIPSIZE_END]

        self.font_desc = pango.FontDescription(gtk.Style().font_desc.to_string())
        self.font_desc.set_size(size * pango.SCALE)
        self.text = text
        self.color = color
        self.size = size
        self.alignment = alignment


    def __setattr__(self, name, val):
        self.__dict__[name] = val

        if name == "width":
            # setting width means consumer wants to contrain the label
            if val is None or val == -1:
                self.__dict__['_bounds_width'] = -1
            else:
                self.__dict__['_bounds_width'] = val * pango.SCALE

        if name in ("text", "size"):
            self._set_dimensions()


    def draw_shape(self):
        self._set_dimensions()
        self.graphics.move_to(0, 0) #make sure we don't wander off somewhere nowhere

        if self.color:
            self.graphics.set_color(self.color)

        self.graphics.show_layout(self.text, self.font_desc,
                                  self.alignment,
                                  self._bounds_width,
                                  self.wrap,
                                  self.ellipsize)

        if self.interactive: #if label is interactive, draw invisible bounding box for simple hit calculations
            self.graphics.set_color("#000", 0)
            self.graphics.rectangle(0,0, self.width, self.height)
            self.graphics.stroke()


    def _set_dimensions(self):
        context = gtk.gdk.CairoContext(cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0,0)))
        layout = context.create_layout()
        layout.set_font_description(self.font_desc)
        layout.set_text(self.text)

        layout.set_width(self._bounds_width)
        if self.wrap:
            layout.set_wrap(self.wrap)
        else:
            layout.set_ellipsize(self.ellipsize or pango.ELLIPSIZE_END)

        # TODO - the __dict__ part look rather lame but allows to circumvent the setattr
        self.__dict__['width'], self.height = layout.get_pixel_size()


class Rectangle(Shape):
    def __init__(self, w, h, corner_radius = 0, **kwargs):
        self.width, self.height, self.corner_radius = w, h, corner_radius
        Shape.__init__(self, **kwargs)

    def draw_shape(self):
        self.graphics.rectangle(0, 0, self.width, self.height, self.corner_radius)


class Polygon(Shape):
    def __init__(self, points, **kwargs):
        self.points = points
        Shape.__init__(self, **kwargs)

    def draw_shape(self):
        if not self.points: return

        self.graphics.move_to(*self.points[0])
        for point in self.points:
            self.graphics.line_to(*point)
        self.graphics.close_path()

class Circle(Shape):
    def __init__(self, radius, **kwargs):
        self.radius = radius
        Shape.__init__(self, **kwargs)

    def draw_shape(self):
        self.graphics.move_to(self.radius * 2, self.radius)
        self.graphics.arc(self.radius, self.radius, self.radius, 0, math.pi * 2)



class Scene(gtk.DrawingArea):
    """ Widget for displaying sprites.
        Add sprites to the Scene by calling :func:`add_child`.
        Scene is descendant of `gtk.DrawingArea <http://www.pygtk.org/docs/pygtk/class-gtkdrawingarea.html>`_
        and thus inherits all it's methods and everything.
    """

    __gsignals__ = {
        "expose-event": "override",
        "configure_event": "override",
        "on-enter-frame": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "on-finish-frame": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "on-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-mouse-move": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-up": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-out": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, interactive = True, framerate = 80):
        gtk.DrawingArea.__init__(self)
        if interactive:
            self.set_events(gtk.gdk.POINTER_MOTION_MASK
                            | gtk.gdk.LEAVE_NOTIFY_MASK | gtk.gdk.ENTER_NOTIFY_MASK
                            | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK)
            self.connect("motion_notify_event", self.__on_mouse_move)
            self.connect_after("enter_notify_event", self.__on_mouse_enter)
            self.connect_after("leave_notify_event", self.__on_mouse_leave)
            self.connect("button_press_event", self.__on_button_press)
            self.connect("button_release_event", self.__on_button_release)

        self.sprites = []
        self.framerate = framerate # frame rate

        self.width, self.height = None, None

        if pytweener:
            self.tweener = pytweener.Tweener(0.4, pytweener.Easing.Cubic.ease_in_out)

        self.colors = Colors

        self.__drawing_queued = False

        self._last_frame_time = None
        self._mouse_sprites = set()
        self._mouse_drag = None
        self._drag_sprite = None
        self._drag_x, self._drag_y = None, None
        self._button_press_time = None # to distinguish between click and drag
        self.mouse_x, self.mouse_y = None, None

        self._debug_bounds = False
        self._mouse_in = False


    def add_child(self, *sprites):
        """Add one or several :class:`graphics.Sprite` sprites to scene """
        for sprite in sprites:
            self.sprites.append(sprite)

    def clear(self):
        """Remove all sprites from scene"""
        self.sprites = []

    def redraw(self):
        """Queue redraw. The redraw will be performed not more often than
           the `framerate` allows"""
        if not self.__drawing_queued: #if we are moving, then there is a timeout somewhere already
            self.__drawing_queued = True
            self._last_frame_time = dt.datetime.now()
            gobject.timeout_add(1000 / self.framerate, self.__interpolate)

    """ animation bits """
    def __interpolate(self):
        if not self.window: #will wait until window comes
            return True

        time_since_last_frame = (dt.datetime.now() - self._last_frame_time).microseconds / 1000000.0
        if pytweener:
            self.tweener.update(time_since_last_frame)

        self.__drawing_queued = pytweener and self.tweener.has_tweens()

        self.queue_draw() # this will trigger do_expose_event when the current events have been flushed

        self._last_frame_time = dt.datetime.now()
        return self.__drawing_queued


    def animate(self, sprite, instant = True, duration = None, easing = None, on_complete = None, on_update = None, delay = None, **kwargs):
        """Interpolate attributes of the given object using the internal tweener
           and redrawing scene after every tweener update.
           Specify the sprite and sprite's attributes that need changing.
           `duration` defaults to 0.4 seconds and `easing` to cubic in-out
           (for others see pytweener.Easing class).

           By default redraw is requested right after creating the animation.
           If you would like to add several tweens and only then redraw,
           set `instant` to False.
           Example::
             # tween some_sprite to coordinates (50,100) using default duration and easing
             scene.animate(some_sprite, x = 50, y = 100)
        """
        if not pytweener: # here we complain
            raise Exception("pytweener not found. Include it to enable animations")

        self.tweener.add_tween(sprite, duration = duration, easing = easing, on_complete = on_complete, on_update = on_update, delay = delay, **kwargs)

        if instant:
            self.redraw()

    """ exposure events """
    def do_configure_event(self, event):
        (self.width, self.height) = self.window.get_size()

    def do_expose_event(self, event):
        self.width, self.height = self.window.get_size()
        context = self.window.cairo_create()

        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()

        alloc = self.get_allocation()  #x, y, width, height
        self.width, self.height = alloc.width, alloc.height

        self.emit("on-enter-frame", context)

        for sprite in self.sprites:
            sprite._draw(context)

        self._check_mouse(self.mouse_x, self.mouse_y)


        if self._debug_bounds:
            context.set_line_width(1)
            context.set_source_rgb(.2, .2, .5)
            for sprite in self.all_sprites():
                if sprite.graphics.extents:
                    x,y,x2,y2 = sprite.graphics.extents
                    context.rectangle(x, y, x2-x, y2-y)
            context.stroke()

        self.emit("on-finish-frame", context)


    """ mouse events """
    def all_sprites(self, sprites = None):
        """returns flat list of the sprite tree for simplified iteration"""

        if sprites is None:
            sprites = self.sprites

        for sprite in sprites:
            yield sprite
            if sprite.sprites:
                for child in self.all_sprites(sprite.sprites):
                    yield child


    def __on_mouse_move(self, area, event):
        mouse_x = event.x
        mouse_y = event.y
        state = event.state
        self.mouse_x, self.mouse_y = mouse_x, mouse_y


        if self._drag_sprite and self._drag_sprite.draggable and gtk.gdk.BUTTON1_MASK & event.state:
            self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))

            # dragging around
            drag = self._mouse_drag and (self._mouse_drag[0] - event.x) ** 2 + \
                                        (self._mouse_drag[1] - event.y) ** 2 > 5 ** 2
            if drag:
                matrix = cairo.Matrix()
                if self._drag_sprite.parent:
                    # TODO - this currently works only until second level - take all parents into account
                    matrix.rotate(self._drag_sprite.parent.rotation)
                    matrix.invert()

                if not self._drag_x:
                    x1,y1 = matrix.transform_point(self._mouse_drag[0], self._mouse_drag[1])

                    self._drag_x = self._drag_sprite.x - x1
                    self._drag_y = self._drag_sprite.y - y1

                mouse_x, mouse_y = matrix.transform_point(mouse_x, mouse_y)
                new_x = mouse_x + self._drag_x
                new_y = mouse_y + self._drag_y


                self._drag_sprite.x, self._drag_sprite.y = new_x, new_y
                self._drag_sprite._on_drag(new_x, new_y)
                self.emit("on-drag", self._drag_sprite, (new_x, new_y))
                self.redraw()

                return
        else:
            if not self.__drawing_queued: # avoid double mouse checks - the redraw will also check for mouse!
                self._check_mouse(event.x, event.y)

        self.emit("on-mouse-move", event)


    def _check_mouse(self, mouse_x, mouse_y):
        if mouse_x is None or not self._mouse_in:
            return

        #check if we have a mouse over
        over = set()

        cursor = gtk.gdk.ARROW

        for sprite in self.all_sprites():
            if sprite.interactive and self._check_hit(sprite, mouse_x, mouse_y):
                if sprite.draggable:
                    cursor = gtk.gdk.FLEUR
                else:
                    cursor = gtk.gdk.HAND2

                over.add(sprite)


        new_mouse_overs = over - self._mouse_sprites
        if new_mouse_overs:
            for sprite in new_mouse_overs:
                sprite._on_mouse_over()

            self.emit("on-mouse-over", list(new_mouse_overs))
            self.redraw()


        gone_mouse_overs = self._mouse_sprites - over
        if gone_mouse_overs:
            for sprite in gone_mouse_overs:
                sprite._on_mouse_out()
            self.emit("on-mouse-out", list(gone_mouse_overs))
            self.redraw()


        self._mouse_sprites = over
        self.window.set_cursor(gtk.gdk.Cursor(cursor))


    def __on_mouse_enter(self, area, event):
        self._mouse_in = True

    def __on_mouse_leave(self, area, event):
        self._mouse_in = False
        if self._mouse_sprites:
            self.emit("on-mouse-out", list(self._mouse_sprites))
            self._mouse_sprites = set()
            self.redraw()

    def _check_hit(self, sprite, x, y):
        if sprite == self._drag_sprite:
            return True

        if not sprite.graphics.extents:
            return False

        sprite_x, sprite_y, sprite_x2, sprite_y2 = sprite.graphics.extents

        if sprite_x <= x <= sprite_x2 and sprite_y <= y <= sprite_y2:
            paths = sprite.graphics.paths
            if not paths:
                return True

            context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, self.width, self.height))
            for path in paths:
                context.append_path(path)
            return context.in_fill(x, y)
        else:
            return False


    def __on_button_press(self, area, event):
        x = event.x
        y = event.y
        state = event.state
        self._mouse_drag = (x, y)

        over = None
        for sprite in self.all_sprites():
            if sprite.interactive and self._check_hit(sprite, event.x, event.y):
                over = sprite # last one will take precedence
        self._drag_sprite = over
        self._button_press_time = dt.datetime.now()

    def __on_button_release(self, area, event):
        #if the drag is less than 5 pixles, then we have a click
        click = self._button_press_time and (dt.datetime.now() - self._button_press_time) < dt.timedelta(milliseconds = 300)
        self._button_press_time = None
        self._mouse_drag = None
        self._drag_x, self._drag_y = None, None
        self._drag_sprite = None

        if click:
            targets = []
            for sprite in self.all_sprites():
                if sprite.interactive and self._check_hit(sprite, event.x, event.y):
                    targets.append(sprite)
                    sprite._on_click(event.state)

            self.emit("on-click", event, targets)
        self.emit("on-mouse-up")
