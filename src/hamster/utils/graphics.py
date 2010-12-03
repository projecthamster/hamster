# - coding: utf-8 -

# Copyright (C) 2008-2010 Toms Bauģis <toms.baugis at gmail.com>
# Dual licensed under the MIT or GPL Version 2 licenses.
# See http://github.com/tbaugis/hamster_experiments/blob/master/README.textile

import math
import datetime as dt
import gtk, gobject

import pango, cairo
import re

try:
    import pytweener
except: # we can also live without tweener. Scene.animate will not work
    pytweener = None

import colorsys
from collections import deque

if cairo.version in ('1.8.2', '1.8.4'):
    # in these two cairo versions the matrix multiplication was flipped
    # http://bugs.freedesktop.org/show_bug.cgi?id=19221
    def cairo_matrix_multiply(matrix1, matrix2):
        return matrix2 * matrix1
else:
    def cairo_matrix_multiply(matrix1, matrix2):
        return matrix1 * matrix2


class Colors(object):
    hex_color_normal = re.compile("#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})")
    hex_color_short = re.compile("#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])")
    hex_color_long = re.compile("#([a-fA-F0-9]{4})([a-fA-F0-9]{4})([a-fA-F0-9]{4})")

    def parse(self, color):
        assert color is not None

        #parse color into rgb values
        if isinstance(color, basestring):
            match = self.hex_color_long.match(color)
            if match:
                color = [int(color, 16) / 65535.0 for color in match.groups()]
            else:
                match = self.hex_color_normal.match(color)
                if match:
                    color = [int(color, 16) / 255.0 for color in match.groups()]
                else:
                    match = self.hex_color_short.match(color)
                    color = [int(color + color, 16) / 255.0 for color in match.groups()]

        elif isinstance(color, gtk.gdk.Color):
            color = [color.red / 65535.0,
                     color.green / 65535.0,
                     color.blue / 65535.0]

        else:
            # otherwise we assume we have color components in 0..255 range
            if color[0] > 1 or color[1] > 1 or color[2] > 1:
                color = [c / 255.0 for c in color]

        return color

    def rgb(self, color):
        return [c * 255 for c in self.parse(color)]

    def gdk(self, color):
        c = self.parse(color)
        return gtk.gdk.Color(int(c[0] * 65535.0), int(c[1] * 65535.0), int(c[2] * 65535.0))

    def is_light(self, color):
        # tells you if color is dark or light, so you can up or down the
        # scale for improved contrast
        return colorsys.rgb_to_hls(*self.rgb(color))[1] > 150

    def darker(self, color, step):
        # returns color darker by step (where step is in range 0..255)
        hls = colorsys.rgb_to_hls(*self.rgb(color))
        return colorsys.hls_to_rgb(hls[0], hls[1] - step, hls[2])

    def contrast(self, color, step):
        """if color is dark, will return a lighter one, otherwise darker"""
        hls = colorsys.rgb_to_hls(*self.rgb(color))
        if self.is_light(color):
            return colorsys.hls_to_rgb(hls[0], hls[1] - step, hls[2])
        else:
            return colorsys.hls_to_rgb(hls[0], hls[1] + step, hls[2])
        # returns color darker by step (where step is in range 0..255)

Colors = Colors() # this is a static class, so an instance will do


class Graphics(object):
    """If context is given upon contruction, will perform drawing
       operations on context instantly. Otherwise queues up the drawing
       instructions and performs them in passed-in order when _draw is called
       with context.

       Most of instructions are mapped to cairo functions by the same name.
       Where there are differences, documenation is provided.

       See http://cairographics.org/documentation/pycairo/2/reference/context.html
       for detailed description of the cairo drawing functions.
    """
    def __init__(self, context = None):
        self.context = context
        self.colors = Colors    # pointer to the color utilities instance
        self.extents = None     # bounds of the object, only if interactive
        self.paths = None       # paths for mouse hit checks
        self._last_matrix = None
        self.__new_instructions = [] # instruction set until it is converted into path-based instructions
        self.__instruction_cache = []
        self.cache_surface = None
        self._cache_layout = None

    def clear(self):
        """clear all instructions"""
        self.__new_instructions = []
        self.__instruction_cache = []
        self.paths = []

    @staticmethod
    def _stroke(context): context.stroke()
    def stroke(self, color = None, alpha = 1):
        if color or alpha < 1:self.set_color(color, alpha)
        self._add_instruction(self._stroke,)

    @staticmethod
    def _fill(context): context.fill()
    def fill(self, color = None, alpha = 1):
        if color or alpha < 1:self.set_color(color, alpha)
        self._add_instruction(self._fill,)

    @staticmethod
    def _mask(context, pattern): context.mask(pattern)
    def mask(self, pattern):
        self._add_instruction(self._mask, pattern)

    @staticmethod
    def _stroke_preserve(context): context.stroke_preserve()
    def stroke_preserve(self, color = None, alpha = 1):
        if color or alpha < 1:self.set_color(color, alpha)
        self._add_instruction(self._stroke_preserve,)

    @staticmethod
    def _fill_preserve(context): context.fill_preserve()
    def fill_preserve(self, color = None, alpha = 1):
        if color or alpha < 1:self.set_color(color, alpha)
        self._add_instruction(self._fill_preserve,)

    @staticmethod
    def _new_path(context): context.new_path()
    def new_path(self):
        self._add_instruction(self._new_path,)

    @staticmethod
    def _paint(context): context.paint()
    def paint(self):
        self._add_instruction(self._paint,)

    @staticmethod
    def _set_font_face(context, face): context.set_font_face(face)
    def set_font_face(self, face):
        self._add_instruction(self._set_font_face, face)

    @staticmethod
    def _set_font_size(context, size): context.set_font_size(size)
    def set_font_size(self, size):
        self._add_instruction(self._set_font_size, size)

    @staticmethod
    def _set_source(context, image):
        context.set_source(image)
    def set_source(self, image, x = 0, y = 0):
        self._add_instruction(self._set_source, image)

    @staticmethod
    def _set_source_surface(context, surface, x, y):
        context.set_source_surface(surface, x, y)
    def set_source_surface(self, surface, x = 0, y = 0):
        self._add_instruction(self._set_source_surface, surface, x, y)

    @staticmethod
    def _set_source_pixbuf(context, pixbuf, x, y):
        context.set_source_pixbuf(pixbuf, x, y)
    def set_source_pixbuf(self, pixbuf, x = 0, y = 0):
        self._add_instruction(self._set_source_pixbuf, pixbuf, x, y)

    @staticmethod
    def _save_context(context): context.save()
    def save_context(self):
        self._add_instruction(self._save_context)

    @staticmethod
    def _restore_context(context): context.restore()
    def restore_context(self):
        self._add_instruction(self._restore_context)


    @staticmethod
    def _clip(context): context.clip()
    def clip(self):
        self._add_instruction(self._clip)

    @staticmethod
    def _translate(context, x, y): context.translate(x, y)
    def translate(self, x, y):
        self._add_instruction(self._translate, x, y)

    @staticmethod
    def _rotate(context, radians): context.rotate(radians)
    def rotate(self, radians):
        self._add_instruction(self._rotate, radians)

    @staticmethod
    def _move_to(context, x, y): context.move_to(x, y)
    def move_to(self, x, y):
        self._add_instruction(self._move_to, x, y)

    @staticmethod
    def _line_to(context, x, y): context.line_to(x, y)
    def line_to(self, x, y = None):
        if y is not None:
            self._add_instruction(self._line_to, x, y)
        elif isinstance(x, list) and y is None:
            for x2, y2 in x:
                self._add_instruction(self._line_to, x2, y2)


    @staticmethod
    def _rel_line_to(context, x, y): context.rel_line_to(x, y)
    def rel_line_to(self, x, y = None):
        if x and y:
            self._add_instruction(self._rel_line_to, x, y)
        elif isinstance(x, list) and y is None:
            for x2, y2 in x:
                self._add_instruction(self._rel_line_to, x2, y2)


    @staticmethod
    def _curve_to(context, x, y, x2, y2, x3, y3):
        context.curve_to(x, y, x2, y2, x3, y3)
    def curve_to(self, x, y, x2, y2, x3, y3):
        """draw a curve. (x2, y2) is the middle point of the curve"""
        self._add_instruction(self._curve_to, x, y, x2, y2, x3, y3)

    @staticmethod
    def _close_path(context): context.close_path()
    def close_path(self):
        self._add_instruction(self._close_path,)

    @staticmethod
    def _set_line_width(context, width):
        context.set_line_width(width)
    @staticmethod
    def _set_dash(context, dash, dash_offset = 0):
        context.set_dash(dash, dash_offset)

    def set_line_style(self, width = None, dash = None, dash_offset = 0):
        """change width and dash of a line"""
        if width is not None:
            self._add_instruction(self._set_line_width, width)

        if dash is not None:
            self._add_instruction(self._set_dash, dash, dash_offset)

    def _set_color(self, context, r, g, b, a):
        if a < 1:
            context.set_source_rgba(r, g, b, a)
        else:
            context.set_source_rgb(r, g, b)

    def set_color(self, color, alpha = 1):
        """set active color. You can use hex colors like "#aaa", or you can use
        normalized RGB tripplets (where every value is in range 0..1), or
        you can do the same thing in range 0..65535.
        also consider skipping this operation and specify the color on stroke and
        fill.
        """
        color = self.colors.parse(color) # parse whatever we have there into a normalized triplet
        if len(color) == 4 and alpha is None:
            alpha = color[3]
        r, g, b = color[:3]
        self._add_instruction(self._set_color, r, g, b, alpha)

    @staticmethod
    def _arc(context, x, y, radius, start_angle, end_angle):
        context.arc(x, y, radius, start_angle, end_angle)
    def arc(self, x, y, radius, start_angle, end_angle):
        """draw arc going counter-clockwise from start_angle to end_angle"""
        self._add_instruction(self._arc, x, y, radius, start_angle, end_angle)

    def circle(self, x, y, radius):
        """draw circle"""
        self._add_instruction(self._arc, x, y, radius, 0, math.pi * 2)

    def ellipse(self, x, y, width, height, edges = None):
        """draw 'perfect' ellipse, opposed to squashed circle. works also for
           equilateral polygons"""
        # the automatic edge case is somewhat arbitrary
        steps = edges or max((32, width, height)) / 2

        angle = 0
        step = math.pi * 2 / steps
        points = []
        while angle < math.pi * 2:
            points.append((width / 2.0 * math.cos(angle),
                           height / 2.0 * math.sin(angle)))
            angle += step

        min_x = min((point[0] for point in points))
        min_y = min((point[1] for point in points))

        self.move_to(points[0][0] - min_x + x, points[0][1] - min_y + y)
        for p_x, p_y in points:
            self.line_to(p_x - min_x + x, p_y - min_y + y)
        self.line_to(points[0][0] - min_x + x, points[0][1] - min_y + y)


    @staticmethod
    def _arc_negative(context, x, y, radius, start_angle, end_angle):
        context.arc_negative(x, y, radius, start_angle, end_angle)
    def arc_negative(self, x, y, radius, start_angle, end_angle):
        """draw arc going clockwise from start_angle to end_angle"""
        self._add_instruction(self._arc_negative, x, y, radius, start_angle, end_angle)

    @staticmethod
    def _rounded_rectangle(context, x, y, x2, y2, corner_radius):
        half_corner = corner_radius / 2

        context.move_to(x + corner_radius, y)
        context.line_to(x2 - corner_radius, y)
        context.curve_to(x2 - half_corner, y, x2, y + half_corner, x2, y + corner_radius)
        context.line_to(x2, y2 - corner_radius)
        context.curve_to(x2, y2 - half_corner, x2 - half_corner, y2, x2 - corner_radius, y2)
        context.line_to(x + corner_radius, y2)
        context.curve_to(x + half_corner, y2, x, y2 - half_corner, x, y2 - corner_radius)
        context.line_to(x, y + corner_radius)
        context.curve_to(x, y + half_corner, x + half_corner, y, x + corner_radius, y)

    @staticmethod
    def _rectangle(context, x, y, w, h): context.rectangle(x, y, w, h)
    def rectangle(self, x, y, width, height, corner_radius = 0):
        "draw a rectangle. if corner_radius is specified, will draw rounded corners"
        if corner_radius <= 0:
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


    def fill_stroke(self, fill = None, stroke = None, line_width = None):
        """fill and stroke the drawn area in one go"""
        if line_width: self.set_line_style(line_width)

        if fill and stroke:
            self.fill_preserve(fill)
        elif fill:
            self.fill(fill)

        if stroke:
            self.stroke(stroke)


    @staticmethod
    def _show_layout(context, layout, text, font_desc, alignment, width, wrap, ellipsize):
        layout.set_font_description(font_desc)
        layout.set_markup(text)
        layout.set_width(width or -1)
        layout.set_alignment(alignment)

        if width > 0:
            if wrap is not None:
                layout.set_wrap(wrap)
            else:
                layout.set_ellipsize(ellipsize or pango.ELLIPSIZE_END)

        context.show_layout(layout)

    def create_layout(self, size = None):
        """utility function to create layout with the default font. Size and
        alignment parameters are shortcuts to according functions of the
        pango.Layout"""
        if not self.context:
            # TODO - this is rather sloppy as far as exception goes
            #        should explain better
            raise "Can not create layout without existing context!"

        layout = self.context.create_layout()
        font_desc = pango.FontDescription(gtk.Style().font_desc.to_string())
        if size: font_desc.set_size(size * pango.SCALE)

        layout.set_font_description(font_desc)
        return layout


    def show_label(self, text, size = None, color = None):
        """display text with system's default font"""
        font_desc = pango.FontDescription(gtk.Style().font_desc.to_string())
        if color: self.set_color(color)
        if size: font_desc.set_size(size * pango.SCALE)
        self.show_layout(text, font_desc)


    @staticmethod
    def _show_text(context, text): context.show_text(text)
    def show_text(self, text):
        self._add_instruction(self._show_text, text)

    @staticmethod
    def _text_path(context, text): context.text_path(text)
    def text_path(self, text):
        """this function is most likely to change"""
        self._add_instruction(self._text_path, text)

    def show_layout(self, text, font_desc, alignment = pango.ALIGN_LEFT, width = -1, wrap = None, ellipsize = None):
        """display text. font_desc is string of pango font description
           often handier than calling this function directly, is to create
           a class:Label object
        """
        layout = self._cache_layout = self._cache_layout or gtk.gdk.CairoContext(cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))).create_layout()

        self._add_instruction(self._show_layout, layout, text, font_desc, alignment, width, wrap, ellipsize)

    def _add_instruction(self, function, *params):
        if self.context:
            function(self.context, *params)
        else:
            self.paths = None
            self.__new_instructions.append((function, params))


    def _draw(self, context, opacity):
        """draw accumulated instructions in context"""

        # if we have been moved around, we should update bounds
        fresh_draw = self.__new_instructions and len(self.__new_instructions) > 0
        if fresh_draw: #new stuff!
            self.paths = []
            self.__instruction_cache = self.__new_instructions
            self.__new_instructions = []
        else:
            if not self.__instruction_cache:
                return

        for instruction, args in self.__instruction_cache:
            if fresh_draw and instruction in (self._new_path, self._stroke, self._fill, self._clip):
                self.paths.append(context.copy_path())

            if opacity < 1 and instruction == self._set_color:
                self._set_color(context, args[0], args[1], args[2], args[3] * opacity)
            elif opacity < 1 and instruction == self._paint:
                context.paint_with_alpha(opacity)
            else:
                instruction(context, *args)



    def _draw_as_bitmap(self, context, opacity):
        """
            instead of caching paths, this function caches the whole drawn thing
            use cache_as_bitmap on sprite to enable this mode
        """
        matrix = context.get_matrix()
        matrix_changed = matrix != self._last_matrix
        new_instructions = len(self.__new_instructions) > 0

        if new_instructions or matrix_changed:
            if new_instructions:
                self.__instruction_cache = list(self.__new_instructions)
                self.__new_instructions = deque()

            self.paths = deque()
            self.extents = None

            if not self.__instruction_cache:
                # no instructions - nothing to do
                return

            # instructions that end path
            path_end_instructions = (self._new_path, self._clip, self._stroke, self._fill, self._stroke_preserve, self._fill_preserve)

            # measure the path extents so we know the size of cache surface
            # also to save some time use the context to paint for the first time
            extents = gtk.gdk.Rectangle()
            for instruction, args in self.__instruction_cache:
                if instruction in path_end_instructions:
                    self.paths.append(context.copy_path())

                    ext = context.path_extents()
                    ext = gtk.gdk.Rectangle(int(ext[0]), int(ext[1]),
                                            int(ext[2]-ext[0]), int(ext[3]-ext[1]))
                    if extents.width and extents.height:
                        if ext:
                            extents = extents.union(ext)
                    else:
                        extents = ext


                if instruction in (self._set_source_pixbuf, self._set_source_surface):
                    # draw a rectangle around the pathless instructions so that the extents are correct
                    pixbuf = args[0]
                    x = args[1] if len(args) > 1 else 0
                    y = args[2] if len(args) > 2 else 0
                    self._rectangle(context, x, y, pixbuf.get_width(), pixbuf.get_height())

                if instruction == self._paint and opacity < 1:
                    context.paint_with_alpha(opacity)
                elif instruction == self._set_color and opacity < 1:
                    self._set_color(context, args[0], args[1], args[2], args[3] * opacity)
                else:
                    instruction(context, *args)


            if instruction not in path_end_instructions: # last one
                self.paths.append(context.copy_path())

                ext = context.path_extents()
                if any((extents.x, extents.y, extents.width, extents.height)):
                    if ext:
                        extents = extents.union(gtk.gdk.Rectangle(int(ext[0]), int(ext[1]),
                                                                  int(ext[2]-ext[0]), int(ext[3]-ext[1])))
                else:
                    extents = ext


            # avoid re-caching if we have just moved
            just_transforms = new_instructions == False and \
                              matrix and self._last_matrix \
                              and all([matrix[i] == self._last_matrix[i] for i in range(4)])

            # TODO - this does not look awfully safe
            extents.x += matrix[4]
            extents.y += matrix[5]
            self.extents = extents

            if not just_transforms:

                # now draw the instructions on the caching surface
                w = int(extents.width) + 1
                h = int(extents.height) + 1
                self.cache_surface = context.get_target().create_similar(cairo.CONTENT_COLOR_ALPHA, w, h)
                ctx = gtk.gdk.CairoContext(cairo.Context(self.cache_surface))
                ctx.translate(-extents.x, -extents.y)

                ctx.transform(matrix)
                for instruction, args in self.__instruction_cache:
                    instruction(ctx, *args)

            self._last_matrix = matrix
        else:
            context.save()
            context.identity_matrix()
            context.translate(self.extents.x, self.extents.y)
            context.set_source_surface(self.cache_surface)
            if opacity < 1:
                context.paint_with_alpha(opacity)
            else:
                context.paint()
            context.restore()





class Sprite(gtk.Object):
    """The Sprite class is a basic display list building block: a display list
       node that can display graphics and can also contain children.
       Once you have created the sprite, use Scene's add_child to add it to
       scene
    """

    __gsignals__ = {
        "on-mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-mouse-out": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-mouse-down": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-up": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag-start": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag-finish": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-render": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
    }

    transformation_flags = set(('x', 'y', 'rotation', 'scale_x', 'scale_y', 'pivot_x', 'pivot_y'))
    graphics_unrelated_flags = set(('drag_x', 'drag_y', '_matrix', 'sprites', '_stroke_context'))
    dirty_flags = set(('opacity', 'visible', 'z_order'))

    def __init__(self, x = 0, y = 0,
                 opacity = 1, visible = True,
                 rotation = 0, pivot_x = 0, pivot_y = 0,
                 scale_x = 1, scale_y = 1,
                 interactive = False, draggable = False,
                 z_order = 0, mouse_cursor = None,
                 cache_as_bitmap = False, snap_to_pixel = True):
        gtk.Object.__init__(self)

        #: list of children sprites. Use :func:`add_child` to add sprites
        self.sprites = []

        #: instance of :ref:`graphics` for this sprite
        self.graphics = Graphics()

        #: boolean denoting whether the sprite responds to mouse events
        self.interactive = interactive

        #: boolean marking if sprite can be automatically dragged
        self.draggable = draggable

        #: relative x coordinate of the sprites' rotation point
        self.pivot_x = pivot_x

        #: relative y coordinates of the sprites' rotation point
        self.pivot_y = pivot_y

        #: sprite opacity
        self.opacity = opacity

        #: boolean visibility flag
        self.visible = visible

        #: pointer to parent :class:`Sprite` or :class:`Scene`
        self.parent = None

        #: sprite coordinates
        self.x, self.y = x, y

        #: rotation of the sprite in radians (use :func:`math.degrees` to convert to degrees if necessary)
        self.rotation = rotation

        #: scale X
        self.scale_x = scale_x

        #: scale Y
        self.scale_y = scale_y

        #: drawing order between siblings. The one with the highest z_order will be on top.
        self.z_order = z_order

        #: mouse-over cursor of the sprite. See :meth:`Scene.mouse_cursor`
        #: for possible values
        self.mouse_cursor = mouse_cursor

        #: x position of the cursor within mouse upon drag. change this value
        #: in on-drag-start to adjust drag point
        self.drag_x = 0

        #: y position of the cursor within mouse upon drag. change this value
        #: in on-drag-start to adjust drag point
        self.drag_y = 0

        #: Whether the sprite should be cached as a bitmap. Default: true
        #: Generally good when you have many static sprites
        self.cache_as_bitmap = cache_as_bitmap

        #: Should the sprite coordinates always rounded to full pixel. Default: true
        #: Mostly this is good for performance but in some cases that can lead
        #: to rounding errors in positioning.
        self.snap_to_pixel = snap_to_pixel

        self.__dict__["_sprite_dirty"] = True # flag that indicates that the graphics object of the sprite should be rendered
        self.__dict__["_sprite_moved"] = True # flag that indicates that the graphics object of the sprite should be rendered

        self._matrix = None
        self._prev_parent_matrix = None

        self._extents = None
        self._prev_extents = None




    def __setattr__(self, name, val):
        try:
            setter = self.__class__.__dict__[name].__set__
        except (AttributeError,  KeyError):
            if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
                return
            self.__dict__[name] = val

            if name == 'parent':
                self._prev_parent_matrix = None
                return

            if name == '_prev_parent_matrix':
                self.__dict__['_extents'] = None
                for sprite in self.sprites:
                    sprite._prev_parent_matrix = None
                return


            if name in self.transformation_flags:
                self.__dict__['_matrix'] = None
                self.__dict__['_extents'] = None
                for sprite in self.sprites:
                    sprite._prev_parent_matrix = None


            if name not in (self.transformation_flags ^ self.graphics_unrelated_flags ^ self.dirty_flags):
                self.__dict__["_sprite_dirty"] = True
                self.__dict__['_extents'] = None

            if name == 'opacity' and self.__dict__.get("cache_as_bitmap") and self.__dict__.get("graphics"):
                # invalidating cache for the bitmap version as that paints opacity in the image
                self.graphics._last_matrix = None
            elif name == 'interactive' and self.__dict__.get("graphics"):
                # when suddenly item becomes interactive, it well can be that the extents had not been
                # calculated
                self.graphics._last_matrix = None
            elif name == 'z_order' and self.__dict__.get('parent'):
                self.parent._sort()

        else:
            setter(self, val)


        self.redraw()

    def _sort(self):
        """sort sprites by z_order"""
        self.sprites = sorted(self.sprites, key=lambda sprite:sprite.z_order)

    def add_child(self, *sprites):
        """Add child sprite. Child will be nested within parent"""
        for sprite in sprites:
            if sprite == self:
                raise Exception("trying to add sprite to itself")
            if sprite.parent:
                sprite.x, sprite.y = self.from_scene_coords(*sprite.to_scene_coords())
                sprite.parent.remove_child(sprite)

            self.sprites.append(sprite)
            sprite.parent = self
        self._sort()


    def remove_child(self, *sprites):
        for sprite in sprites:
            self.sprites.remove(sprite)
            sprite.parent = None

    def bring_to_front(self):
        """adjusts sprite's z-order so that the sprite is on top of it's
        siblings"""
        if not self.parent:
            return
        self.z_order = self.parent.sprites[-1].z_order + 1

    def send_to_back(self):
        """adjusts sprite's z-order so that the sprite is behind it's
        siblings"""
        if not self.parent:
            return
        self.z_order = self.parent.sprites[0].z_order - 1


    def get_extents(self):
        """measure the extents of the sprite's graphics. if context is provided
           will use that to draw the paths"""
        if self._extents:
            return self._extents

        context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
        context.transform(self.get_matrix())

        if not self.graphics.paths:
            self.graphics._draw(context, 1)


        if not self.graphics.paths:
            return None


        for path in self.graphics.paths:
            context.append_path(path)
        context.identity_matrix()

        ext = context.path_extents()
        ext = gtk.gdk.Rectangle(int(ext[0]), int(ext[1]),
                                int(ext[2] - ext[0]), int(ext[3] - ext[1]))

        self.__dict__['_extents'] = ext
        self._stroke_context = context
        return ext




    def check_hit(self, x, y):
        """check if the given coordinates are inside the sprite's fill or stroke
           path"""

        extents = self.get_extents()

        if not extents:
            return False

        if extents.x <= x <= extents.x + extents.width and extents.y <= y <= extents.y + extents.height:
            return self._stroke_context.in_fill(x, y)
        else:
            return False

    def get_scene(self):
        """returns class:`Scene` the sprite belongs to"""
        if hasattr(self, 'parent') and self.parent:
            if isinstance(self.parent, Sprite) == False:
                return self.parent
            else:
                return self.parent.get_scene()
        return None

    def redraw(self):
        """queue redraw of the sprite. this function is called automatically
           whenever a sprite attribute changes. sprite changes that happen
           during scene redraw are ignored in order to avoid echoes.
           Call scene.redraw() explicitly if you need to redraw in these cases.
        """
        scene = self.get_scene()
        if scene and scene._redraw_in_progress == False:
            self.parent.redraw()

    def animate(self, duration = None, easing = None, on_complete = None, on_update = None, **kwargs):
        """Request paretn Scene to Interpolate attributes using the internal tweener.
           Specify sprite's attributes that need changing.
           `duration` defaults to 0.4 seconds and `easing` to cubic in-out
           (for others see pytweener.Easing class).

           Example::
             # tween some_sprite to coordinates (50,100) using default duration and easing
             self.animate(x = 50, y = 100)
        """
        scene = self.get_scene()
        if scene:
            scene.animate(self, duration, easing, on_complete, on_update, **kwargs)
        else:
            for key, val in kwargs.items():
                setattr(self, key, val)

    def get_local_matrix(self):
        if not self._matrix:
            self._matrix = cairo.Matrix()

            if self.snap_to_pixel:
                self._matrix.translate(int(self.x) + int(self.pivot_x), int(self.y) + int(self.pivot_y))
            else:
                self._matrix.translate(self.x + self.pivot_x, self.y + self.pivot_y)

            if self.rotation:
                self._matrix.rotate(self.rotation)


            if self.snap_to_pixel:
                self._matrix.translate(int(-self.pivot_x), int(-self.pivot_y))
            else:
                self._matrix.translate(-self.pivot_x, -self.pivot_y)


            if self.scale_x != 1 or self.scale_y != 1:
                self._matrix.scale(self.scale_x, self.scale_y)

        return cairo.Matrix() * self._matrix


    def get_matrix(self):
        """return sprite's current transformation matrix"""
        if self.parent:
            return cairo_matrix_multiply(self.get_local_matrix(),
                                         (self._prev_parent_matrix or self.parent.get_matrix()))
        else:
            return self.get_local_matrix()


    def from_scene_coords(self, x=0, y=0):
        """Converts x, y given in the scene coordinates to sprite's local ones
        coordinates"""
        matrix = self.get_matrix()
        matrix.invert()
        return matrix.transform_point(x, y)

    def to_scene_coords(self, x=0, y=0):
        """Converts x, y from sprite's local coordinates to scene coordinates"""
        return self.get_matrix().transform_point(x, y)

    def _draw(self, context, opacity = 1, parent_matrix = None):
        if self.visible is False:
            return

        if (self._sprite_dirty): # send signal to redo the drawing when sprite is dirty
            self.__dict__['_extents'] = None
            self.emit("on-render")
            self.__dict__["_sprite_dirty"] = False


        parent_matrix = parent_matrix or cairo.Matrix()

        # cache parent matrix
        self._prev_parent_matrix = parent_matrix

        matrix = self.get_local_matrix()
        context.save()
        context.transform(matrix)


        if self.cache_as_bitmap:
            self.graphics._draw_as_bitmap(context, self.opacity * opacity)
        else:
            self.graphics._draw(context, self.opacity * opacity)

        self.__dict__['_prev_extents'] = self._extents or self.get_extents()

        for sprite in self.sprites:
            sprite._draw(context, self.opacity * opacity, cairo_matrix_multiply(matrix, parent_matrix))


        context.restore()
        context.new_path() #forget about us


class BitmapSprite(Sprite):
    """Caches given image data in a surface similar to targets, which ensures
       that drawing it will be quick and low on CPU.
       Image data can be either :class:`cairo.ImageSurface` or :class:`gtk.gdk.Pixbuf`
    """
    def __init__(self, image_data = None, **kwargs):
        Sprite.__init__(self, **kwargs)

        self._image_width, self._image_height = None, None
        #: image data
        self.image_data = image_data

        self._surface = None

    @property
    def height(self):
        return self._image_height

    @property
    def width(self):
        return self._image_width


    def __setattr__(self, name, val):
        Sprite.__setattr__(self, name, val)
        if name == 'image_data':
            self.__dict__['_surface'] = None
            if self.image_data:
                self.__dict__['_image_width'] = self.image_data.get_width()
                self.__dict__['_image_height'] = self.image_data.get_height()

    def _draw(self, context, opacity = 1, parent_matrix = None):
        if self.image_data is None or self.width is None or self.height is None:
            return

        if not self._surface:
            # caching image on surface similar to the target
            surface = context.get_target().create_similar(cairo.CONTENT_COLOR_ALPHA,
                                                               self.width,
                                                               self.height)


            local_context = gtk.gdk.CairoContext(cairo.Context(surface))
            if isinstance(self.image_data, gtk.gdk.Pixbuf):
                local_context.set_source_pixbuf(self.image_data, 0, 0)
            else:
                local_context.set_source_surface(self.image_data)
            local_context.paint()

            # add instructions with the resulting surface
            self.graphics.clear()
            self.graphics.rectangle(0, 0, self.width, self.height)
            self.graphics.clip()
            self.graphics.set_source_surface(surface)
            self.graphics.paint()
            self._surface = surface


        Sprite._draw(self,  context, opacity, parent_matrix)


class Image(BitmapSprite):
    """Displays image by path. Currently supports only PNG images."""
    def __init__(self, path, **kwargs):
        BitmapSprite.__init__(self, **kwargs)

        #: path to the image
        self.path = path

    def __setattr__(self, name, val):
        BitmapSprite.__setattr__(self, name, val)
        if name == 'path': # load when the value is set to avoid penalty on render
            self.image_data = cairo.ImageSurface.create_from_png(self.path)



class Icon(BitmapSprite):
    """Displays icon by name and size in the theme"""
    def __init__(self, name, size=24, **kwargs):
        BitmapSprite.__init__(self, **kwargs)
        self.theme = gtk.icon_theme_get_default()

        #: icon name from theme
        self.name = name

        #: icon size in pixels
        self.size = size

    def __setattr__(self, name, val):
        BitmapSprite.__setattr__(self, name, val)
        if name in ('name', 'size'): # no other reason to discard cache than just on path change
            if self.__dict__.get('name') and self.__dict__.get('size'):
                self.image_data = self.theme.load_icon(self.name, self.size, 0)
            else:
                self.image_data = None


class Label(Sprite):
    __gsignals__ = {
        "on-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }
    def __init__(self, text = "", size = 10, color = None,
                 alignment = pango.ALIGN_LEFT, font_face = None,
                 max_width = None, wrap = None, ellipsize = None,
                 outline_color = None, outline_width = 5,
                 **kwargs):
        Sprite.__init__(self, **kwargs)
        self.width, self.height = None, None


        self._test_context = gtk.gdk.CairoContext(cairo.Context(cairo.ImageSurface(cairo.FORMAT_A8, 0, 0)))
        self._test_layout = self._test_context.create_layout()


        #: pango.FontDescription, default is the system's font
        self.font_desc = pango.FontDescription(gtk.Style().font_desc.to_string())
        self.font_desc.set_size(size * pango.SCALE)

        #: color of label either as hex string or an (r,g,b) tuple
        self.color = color

        #: color for text outline (currently works only with a custom font face)
        self.outline_color = outline_color

        #: text outline thickness (currently works only with a custom font face)
        self.outline_width = outline_width

        self._bounds_width = None

        #: wrapping method. Can be set to pango. [WRAP_WORD, WRAP_CHAR,
        #: WRAP_WORD_CHAR]
        self.wrap = wrap

        #: Ellipsize mode. Can be set to pango. [ELLIPSIZE_NONE,
        #: ELLIPSIZE_START, ELLIPSIZE_MIDDLE, ELLIPSIZE_END]
        self.ellipsize = ellipsize

        #: alignment. one of pango.[ALIGN_LEFT, ALIGN_RIGHT, ALIGN_CENTER]
        self.alignment = alignment

        #: label's `FontFace <http://www.cairographics.org/documentation/pycairo/2/reference/text.html#cairo.FontFace>`_
        self.font_face = font_face

        #: font size
        self.size = size


        #: maximum  width of the label in pixels. if specified, the label
        #: will be wrapped or ellipsized depending on the wrap and ellpisize settings
        self.max_width = max_width

        self._ascent = None # used to determine Y position for when we have a font face

        self.__surface = None

        #: label text
        self.text = text

        self._letter_sizes = {}
        self._measures = {}


        self.connect("on-render", self.on_render)

        self.graphics_unrelated_flags = self.graphics_unrelated_flags ^ set(("_letter_sizes", "__surface", "_ascent", "_bounds_width", "_measures"))


    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") != val:
            if name == "width" and val and self.__dict__.get('_bounds_width') and val * pango.SCALE == self.__dict__['_bounds_width']:
                return

            Sprite.__setattr__(self, name, val)


            if name == "width":
                # setting width means consumer wants to contrain the label
                if val is None or val == -1:
                    self.__dict__['_bounds_width'] = None
                else:
                    self.__dict__['_bounds_width'] = val * pango.SCALE

            if name in ("width", "text", "size", "font_desc", "wrap", "ellipsize", "max_width"):
                self._measures = {}
                # avoid chicken and egg
                if hasattr(self, "text") and hasattr(self, "size") and hasattr(self, "font_face"):
                    self.__dict__['width'], self.__dict__['height'], self.__dict__['_ascent'] = self.measure(self.text)

            if name in("font_desc", "size"):
                self._letter_sizes = {}

            if name == 'text':
                self.emit('on-change')


    def _wrap(self, text):
        """wrapping text ourselves when we can't use pango"""
        if not text:
            return [], 0

        context = self._test_context
        context.set_font_face(self.font_face)
        context.set_font_size(self.size)


        if (not self._bounds_width and not self.max_width) or self.wrap is None:
            return [(text, context.text_extents(text)[4])], context.font_extents()[2]


        width = self.max_width or self.width

        letters = {}
        # measure individual letters
        if self.wrap in (pango.WRAP_CHAR, pango.WRAP_WORD_CHAR):
            letters = set(unicode(text))
            sizes = [self._letter_sizes.setdefault(letter, context.text_extents(letter)[4]) for letter in letters]
            letters = dict(zip(letters, sizes))


        line = ""
        lines = []
        running_width = 0

        if self.wrap in (pango.WRAP_WORD, pango.WRAP_WORD_CHAR):
            # if we wrap by word then we split the whole thing in words
            # and stick together while they fit. in case if the word does not
            # fit at all, we break it in pieces
            while text:
                fragment, fragment_length = "", 0

                word = re.search("\s", text)
                if word:
                    fragment = text[:word.start()+1]
                else:
                    fragment = text

                fragment_length = context.text_extents(fragment)[4]


                if (fragment_length > width) and self.wrap == pango.WRAP_WORD_CHAR:
                    # too big to fit in any way
                    # split in pieces so that we fit in current row as much
                    # as we can and trust the task of putting things in next row
                    # to the next run
                    while fragment and running_width + fragment_length > width:
                        fragment_length -= letters[fragment[-1]]
                        fragment = fragment[:-1]

                    lines.append((line + fragment, running_width + fragment_length))
                    running_width = 0
                    fragment_length = 0
                    line = ""



                else:
                    # otherwise the usual squishing
                    if running_width + fragment_length <= width:
                        line += fragment
                    else:
                        lines.append((line, running_width))
                        running_width = 0
                        line = fragment



                running_width += fragment_length
                text = text[len(fragment):]

        elif self.wrap == pango.WRAP_CHAR:
            # brute force glueing while we have space
            for fragment in text:
                fragment_length = letters[fragment]

                if running_width + fragment_length <= width:
                    line += fragment
                else:
                    lines.append((line, running_width))
                    running_width = 0
                    line = fragment

                running_width += fragment_length

        if line:
            lines.append((line, running_width))

        return lines, context.font_extents()[2]




    def measure(self, text):
        """measures given text with label's font and size.
        returns width, height and ascent. Ascent's null in case if the label
        does not have font face specified (and is thusly using pango)"""

        if text in self._measures:
            return self._measures[text]

        width, height, ascent = None, None, None

        context = self._test_context
        if self.font_face:
            context.set_font_face(self.font_face)
            context.set_font_size(self.size)
            font_ascent, font_descent, font_height = context.font_extents()[:3]

            if self._bounds_width or self.max_width:
                lines, line_height = self._wrap(text)

                if self._bounds_width:
                    width = self._bounds_width / pango.SCALE
                else:
                    max_width = 0
                    for line, line_width in lines:
                        max_width = max(max_width, line_width)
                    width = max_width

                height = len(lines) * line_height
                ascent = font_ascent
            else:
                width = context.text_extents(text)[4]
                ascent, height = font_ascent, font_ascent + font_descent

        else:
            layout = self._test_layout
            layout.set_font_description(self.font_desc)
            layout.set_markup(text)
            layout.set_width((self._bounds_width or -1))
            layout.set_ellipsize(pango.ELLIPSIZE_NONE)


            if self.wrap is not None:
                layout.set_wrap(self.wrap)
            else:
                layout.set_ellipsize(self.ellipsize or pango.ELLIPSIZE_END)

            width, height = layout.get_pixel_size()


        self._measures[text] = width, height, ascent

        return self._measures[text]


    def on_render(self, sprite):
        if not self.text:
            self.graphics.clear()
            return

        self.graphics.set_color(self.color)

        rect_width = self.width

        if self.font_face:
            self.graphics.set_font_size(self.size)
            self.graphics.set_font_face(self.font_face)
            if self._bounds_width or self.max_width:
                lines, line_height = self._wrap(self.text)

                x, y = 0.5, int(self._ascent) + 0.5
                for line, line_width in lines:
                    if self.alignment == pango.ALIGN_RIGHT:
                        x = self.width - line_width
                    elif self.alignment == pango.ALIGN_CENTER:
                        x = (self.width - line_width) / 2

                    if self.outline_color:
                        self.graphics.save_context()
                        self.graphics.move_to(x, y)
                        self.graphics.text_path(line)
                        self.graphics.set_line_style(width=self.outline_width)
                        self.graphics.fill_stroke(self.outline_color, self.outline_color)
                        self.graphics.restore_context()

                    self.graphics.move_to(x, y)
                    self.graphics.set_color(self.color)
                    self.graphics.show_text(line)

                    y += line_height

            else:
                if self.outline_color:
                    self.graphics.save_context()
                    self.graphics.move_to(0, self._ascent)
                    self.graphics.text_path(self.text)
                    self.graphics.set_line_style(width=self.outline_width)
                    self.graphics.fill_stroke(self.outline_color, self.outline_color)
                    self.graphics.restore_context()

                self.graphics.move_to(0, self._ascent)
                self.graphics.show_text(self.text)

        else:
            self.graphics.show_layout(self.text, self.font_desc,
                                      self.alignment,
                                      self._bounds_width,
                                      self.wrap,
                                      self.ellipsize)

            if self._bounds_width:
                rect_width = self._bounds_width / pango.SCALE

        self.graphics.rectangle(0, 0, rect_width, self.height)
        self.graphics.clip()



class Rectangle(Sprite):
    def __init__(self, w, h, corner_radius = 0, fill = None, stroke = None, line_width = 1, **kwargs):
        Sprite.__init__(self, **kwargs)

        #: width
        self.width = w

        #: height
        self.height = h

        #: fill color
        self.fill = fill

        #: stroke color
        self.stroke = stroke

        #: stroke line width
        self.line_width = line_width

        #: corner radius. Set bigger than 0 for rounded corners
        self.corner_radius = corner_radius
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.set_line_style(width = self.line_width)
        self.graphics.rectangle(0, 0, self.width, self.height, self.corner_radius)
        self.graphics.fill_stroke(self.fill, self.stroke, self.line_width)


class Polygon(Sprite):
    def __init__(self, points, fill = None, stroke = None, line_width = 1, **kwargs):
        Sprite.__init__(self, **kwargs)

        #: list of (x,y) tuples that the line should go through. Polygon
        #: will automatically close path.
        self.points = points

        #: fill color
        self.fill = fill

        #: stroke color
        self.stroke = stroke

        #: stroke line width
        self.line_width = line_width

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        if not self.points: return

        self.graphics.move_to(*self.points[0])
        self.graphics.line_to(self.points)
        self.graphics.close_path()

        self.graphics.fill_stroke(self.fill, self.stroke, self.line_width)


class Circle(Sprite):
    def __init__(self, width, height, fill = None, stroke = None, line_width = 1, **kwargs):
        Sprite.__init__(self, **kwargs)

        #: circle width
        self.width = width

        #: circle height
        self.height = height

        #: fill color
        self.fill = fill

        #: stroke color
        self.stroke = stroke

        #: stroke line width
        self.line_width = line_width

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        if self.width == self.height:
            radius = self.width / 2.0
            self.graphics.circle(radius, radius, radius)
        else:
            self.graphics.ellipse(0, 0, self.width, self.height)

        self.graphics.fill_stroke(self.fill, self.stroke, self.line_width)


class Scene(gtk.DrawingArea):
    """ Drawing area for displaying sprites.
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
        "on-drag-start": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag-finish": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),

        "on-mouse-move": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-down": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-up": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-out": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),

        "on-scroll": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, interactive = True, framerate = 60,
                       background_color = None, scale = False, keep_aspect = True):
        gtk.DrawingArea.__init__(self)
        if interactive:
            self.set_events(gtk.gdk.POINTER_MOTION_MASK
                            | gtk.gdk.LEAVE_NOTIFY_MASK | gtk.gdk.ENTER_NOTIFY_MASK
                            | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK
                            | gtk.gdk.SCROLL_MASK
                            | gtk.gdk.KEY_PRESS_MASK)
            self.connect("motion_notify_event", self.__on_mouse_move)
            self.connect("enter_notify_event", self.__on_mouse_enter)
            self.connect("leave_notify_event", self.__on_mouse_leave)
            self.connect("button_press_event", self.__on_button_press)
            self.connect("button_release_event", self.__on_button_release)
            self.connect("scroll-event", self.__on_scroll)

        #: list of sprites in scene. use :func:`add_child` to add sprites
        self.sprites = []

        #: framerate of animation. This will limit how often call for
        #: redraw will be performed (that is - not more often than the framerate). It will
        #: also influence the smoothness of tweeners.
        self.framerate = framerate

        #: Scene width. Will be `None` until first expose (that is until first
        #: on-enter-frame signal below).
        self.width = None

        #: Scene height. Will be `None` until first expose (that is until first
        #: on-enter-frame signal below).
        self.height = None

        #: instance of :class:`pytweener.Tweener` that is used by
        #: :func:`animate` function, but can be also accessed directly for advanced control.
        self.tweener = None
        if pytweener:
            self.tweener = pytweener.Tweener(0.4, pytweener.Easing.Cubic.ease_in_out)

        #: instance of :class:`Colors` class for color parsing
        self.colors = Colors

        #: read only info about current framerate (frames per second)
        self.fps = 0 # inner frames per second counter

        #: Last known x position of the mouse (set on expose event)
        self.mouse_x = None

        #: Last known y position of the mouse (set on expose event)
        self.mouse_y = None

        #: Background color of the scene. Use either a string with hex color or an RGB triplet.
        self.background_color = background_color

        #: Mouse cursor appearance.
        #: Replace with your own cursor or set to False to have no cursor.
        #: None will revert back the default behavior
        self.mouse_cursor = None

        blank_pixmap = gtk.gdk.Pixmap(None, 1, 1, 1)
        self._blank_cursor = gtk.gdk.Cursor(blank_pixmap, blank_pixmap, gtk.gdk.Color(), gtk.gdk.Color(), 0, 0)


        #: Miminum distance in pixels for a drag to occur
        self.drag_distance = 1

        self._last_frame_time = None
        self._mouse_sprite = None
        self._drag_sprite = None
        self._mouse_down_sprite = None
        self.__drag_started = False
        self.__drag_start_x, self.__drag_start_y = None, None

        self._mouse_in = False
        self.__last_cursor = None

        self.__drawing_queued = False
        self._redraw_in_progress = False

        #: When specified, upon window resize the content will be scaled
        #: relative to original window size. Defaults to False.
        self.scale = scale

        #: Should the stage maintain aspect ratio upon scale if
        #: :attr:`Scene.scale` is enabled. Defaults to true.
        self.keep_aspect = keep_aspect

        self._original_width, self._original_height = None,  None



    def add_child(self, *sprites):
        """Add one or several :class:`Sprite` objects to the scene"""
        for sprite in sprites:
            if sprite == self:
                raise Exception("trying to add sprite to itself")
            if sprite.parent:
                sprite.x, sprite.y = sprite.to_scene_coords(0, 0)
                sprite.parent.remove_child(sprite)
            self.sprites.append(sprite)
            sprite.parent = self
        self._sort()

    def _sort(self):
        """sort sprites by z_order"""
        self.sprites = sorted(self.sprites, key=lambda sprite:sprite.z_order)


    def remove_child(self, *sprites):
        """Remove one or several :class:`Sprite` sprites from scene """
        for sprite in sprites:
            self.sprites.remove(sprite)
            sprite.parent = None

    # these two mimic sprite functions so parent check can be avoided
    def from_scene_coords(self, x, y): return x, y
    def to_scene_coords(self, x, y): return x, y
    def get_matrix(self): return cairo.Matrix()

    def clear(self):
        """Remove all sprites from scene"""
        self.remove_child(*self.sprites)

    def animate(self, sprite, duration = None, easing = None, on_complete = None, on_update = None, **kwargs):
        """Interpolate attributes of the given object using the internal tweener
           and redrawing scene after every tweener update.
           Specify the sprite and sprite's attributes that need changing.
           `duration` defaults to 0.4 seconds and `easing` to cubic in-out
           (for others see pytweener.Easing class).

           Redraw is requested right after creating the animation.
           Example::

             # tween some_sprite to coordinates (50,100) using default duration and easing
             scene.animate(some_sprite, x = 50, y = 100)
        """
        if not self.tweener: # here we complain
            raise Exception("pytweener was not found. Include it to enable animations")

        tween = self.tweener.add_tween(sprite,
                                       duration=duration,
                                       easing=easing,
                                       on_complete=on_complete,
                                       on_update=on_update,
                                       **kwargs)
        self.redraw()
        return tween


    def redraw(self):
        """Queue redraw. The redraw will be performed not more often than
           the `framerate` allows"""
        if self.__drawing_queued == False: #if we are moving, then there is a timeout somewhere already
            self.__drawing_queued = True
            self._last_frame_time = dt.datetime.now()
            gobject.timeout_add(1000 / self.framerate, self.__redraw_loop)

    def __redraw_loop(self):
        """loop until there is nothing more to tween"""
        self.queue_draw() # this will trigger do_expose_event when the current events have been flushed

        self.__drawing_queued = self.tweener and self.tweener.has_tweens()
        return self.__drawing_queued


    def do_expose_event(self, event):
        context = self.window.cairo_create()

        # clip to the visible part
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        if self.background_color:
            color = self.colors.parse(self.background_color)
            context.set_source_rgb(*color)
            context.fill_preserve()
        context.clip()

        if self.scale:
            aspect_x = self.width / self._original_width
            aspect_y = self.height / self._original_height
            if self.keep_aspect:
                aspect_x = aspect_y = min(aspect_x, aspect_y)
            context.scale(aspect_x, aspect_y)

        self.mouse_x, self.mouse_y, mods = self.get_window().get_pointer()

        self._redraw_in_progress = True

        # update tweens
        now = dt.datetime.now()
        delta = (now - (self._last_frame_time or dt.datetime.now())).microseconds / 1000000.0
        self._last_frame_time = now
        if self.tweener:
            self.tweener.update(delta)

        self.fps = 1 / delta


        # start drawing
        self.emit("on-enter-frame", context)
        for sprite in self.sprites:
            sprite._draw(context)

        self.__check_mouse(self.mouse_x, self.mouse_y)
        self.emit("on-finish-frame", context)
        self._redraw_in_progress = False


    def do_configure_event(self, event):
        if self._original_width is None:
            self._original_width = float(event.width)
            self._original_height = float(event.height)

        self.width, self.height = event.width, event.height

    def all_visible_sprites(self):
        """Returns flat list of the sprite tree for simplified iteration"""
        def all_recursive(sprites):
            for sprite in sprites:
                if sprite.visible:
                    yield sprite
                    if sprite.sprites:
                        for child in all_recursive(sprite.sprites):
                            yield child

        return all_recursive(self.sprites)


    def get_sprite_at_position(self, x, y):
        """Returns the topmost visible interactive sprite for given coordinates"""
        over = None



        for sprite in self.all_visible_sprites():
            if (sprite.interactive or sprite.draggable) and sprite.check_hit(x, y):
                over = sprite

        return over



    def __check_mouse(self, x, y):
        if x is None or self._mouse_in == False:
            return

        cursor = gtk.gdk.ARROW # default

        if self.mouse_cursor is not None:
            cursor = self.mouse_cursor

        if self._drag_sprite:
            cursor = self._drag_sprite.mouse_cursor or self.mouse_cursor or gtk.gdk.FLEUR
        else:
            #check if we have a mouse over
            over = self.get_sprite_at_position(x, y)
            if self._mouse_sprite and self._mouse_sprite != over:
                self._mouse_sprite.emit("on-mouse-out")
                self.emit("on-mouse-out", self._mouse_sprite)
                self.redraw()

            if over:
                if over.mouse_cursor is not None:
                    cursor = over.mouse_cursor

                elif self.mouse_cursor is None:
                    # resort to defaults
                    if over.draggable:
                        cursor = gtk.gdk.FLEUR
                    else:
                        cursor = gtk.gdk.HAND2

                if over != self._mouse_sprite:
                    over.emit("on-mouse-over")
                    self.emit("on-mouse-over", over)
                    self.redraw()

            self._mouse_sprite = over

        if cursor == False:
            cursor = self._blank_cursor

        if not self.__last_cursor or cursor != self.__last_cursor:
            if isinstance(cursor, gtk.gdk.Cursor):
                self.window.set_cursor(cursor)
            else:
                self.window.set_cursor(gtk.gdk.Cursor(cursor))

            self.__last_cursor = cursor


    """ mouse events """
    def __on_mouse_move(self, area, event):
        state = event.state


        if self._mouse_down_sprite and self._mouse_down_sprite.draggable \
           and gtk.gdk.BUTTON1_MASK & event.state:
            # dragging around
            drag_started = (self.__drag_start_x is not None and \
                           (self.__drag_start_x - event.x) ** 2 + \
                           (self.__drag_start_y - event.y) ** 2 > self.drag_distance ** 2)

            if drag_started and not self.__drag_started:
                self._drag_sprite = self._mouse_down_sprite

                self._drag_sprite.drag_x, self._drag_sprite.drag_y = self._drag_sprite.x, self._drag_sprite.y

                self._drag_sprite.emit("on-drag-start", event)
                self.emit("on-drag-start", self._drag_sprite, event)
                self.redraw()


            self.__drag_started = self.__drag_started or drag_started

            if self.__drag_started:
                diff_x, diff_y = event.x - self.__drag_start_x, event.y - self.__drag_start_y
                if isinstance(self._drag_sprite.parent, Sprite):
                    matrix = self._drag_sprite.parent.get_matrix()
                    matrix.invert()
                    diff_x, diff_y = matrix.transform_distance(diff_x, diff_y)

                self._drag_sprite.x, self._drag_sprite.y = self._drag_sprite.drag_x + diff_x, self._drag_sprite.drag_y + diff_y

                self._drag_sprite.emit("on-drag", event)
                self.emit("on-drag", self._drag_sprite, event)
                self.redraw()

        else:
            # avoid double mouse checks - the redraw will also check for mouse!
            if not self.__drawing_queued:
                self.__check_mouse(event.x, event.y)

        self.emit("on-mouse-move", event)

    def __on_mouse_enter(self, area, event):
        self._mouse_in = True

    def __on_mouse_leave(self, area, event):
        self._mouse_in = False
        if self._mouse_sprite:
            self.emit("on-mouse-out", self._mouse_sprite)
            self.redraw()
            self._mouse_sprite = None


    def __on_button_press(self, area, event):
        target = self.get_sprite_at_position(event.x, event.y)
        self.__drag_start_x, self.__drag_start_y = event.x, event.y

        self._mouse_down_sprite = target

        if target:
            target.emit("on-mouse-down", event)
        self.emit("on-mouse-down", event)

    def __on_button_release(self, area, event):
        target = self.get_sprite_at_position(event.x, event.y)

        if target:
            target.emit("on-mouse-up", event)
        self.emit("on-mouse-up", event)

        # trying to not emit click and drag-finish at the same time
        click = not self.__drag_started or (event.x - self.__drag_start_x) ** 2 + \
                                           (event.y - self.__drag_start_y) ** 2 < self.drag_distance
        if (click and self.__drag_started == False) or not self._drag_sprite:
            if target:
                target.emit("on-click", event)

            self.emit("on-click", event, target)
            self.redraw()

        if self._drag_sprite:
            self._drag_sprite.emit("on-drag-finish", event)
            self.emit("on-drag-finish", self._drag_sprite, event)
            self.redraw()

            self._drag_sprite.drag_x, self._drag_sprite.drag_y = None, None
            self._drag_sprite = None
        self._mouse_down_sprite = None

        self.__drag_started = False
        self.__drag_start_x, self__drag_start_y = None, None

    def __on_scroll(self, area, event):
        self.emit("on-scroll", event)
