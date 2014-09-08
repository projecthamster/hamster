# - coding: utf-8 -

# Copyright (c) 2008-2012 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.
# See http://github.com/tbaugis/hamster_experiments/blob/master/README.textile

from collections import defaultdict
import math
import datetime as dt


from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import Pango as pango
from gi.repository import PangoCairo as pangocairo

import cairo
from gi.repository import GdkPixbuf

import re

try:
    import pytweener
except: # we can also live without tweener. Scene.animate will not work
    pytweener = None

import colorsys
from collections import deque

# lemme know if you know a better way how to get default font
_test_label = gtk.Label("Hello")
_font_desc = _test_label.get_style().font_desc.to_string()


class ColorUtils(object):
    hex_color_normal = re.compile("#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})")
    hex_color_short = re.compile("#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])")
    hex_color_long = re.compile("#([a-fA-F0-9]{4})([a-fA-F0-9]{4})([a-fA-F0-9]{4})")

    # d3 colors
    category10 = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf")
    category20 = ("#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c",
                  "#98df8a", "#d62728", "#ff9896", "#9467bd", "#c5b0d5",
                  "#8c564b", "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f",
                  "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5")
    category20b = ("#393b79", "#5254a3", "#6b6ecf", "#9c9ede", "#637939",
                   "#8ca252", "#b5cf6b", "#cedb9c", "#8c6d31", "#bd9e39",
                   "#e7ba52", "#e7cb94", "#843c39", "#ad494a", "#d6616b",
                   "#e7969c", "#7b4173", "#a55194", "#ce6dbd", "#de9ed6")
    category20c = ("#3182bd", "#6baed6", "#9ecae1", "#c6dbef", "#e6550d",
                   "#fd8d3c", "#fdae6b", "#fdd0a2", "#31a354", "#74c476",
                   "#a1d99b", "#c7e9c0", "#756bb1", "#9e9ac8", "#bcbddc",
                   "#dadaeb", "#636363", "#969696", "#bdbdbd", "#d9d9d9")

    def parse(self, color):
        """parse string or a color tuple into color usable for cairo (all values
        in the normalized (0..1) range"""
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

        elif isinstance(color, gdk.Color):
            color = [color.red / 65535.0,
                     color.green / 65535.0,
                     color.blue / 65535.0]

        elif isinstance(color, (list, tuple)):
            # otherwise we assume we have color components in 0..255 range
            if color[0] > 1 or color[1] > 1 or color[2] > 1:
                color = [c / 255.0 for c in color]
        else:
            color = [color.red, color.green, color.blue]


        return color

    def rgb(self, color):
        """returns rgb[a] tuple of the color with values in range 0.255"""
        return [c * 255 for c in self.parse(color)]

    def gdk(self, color):
        """returns gdk.Color object of the given color"""
        c = self.parse(color)
        return gdk.Color.from_floats(c)

    def hex(self, color):
        c = self.parse(color)
        return "#" + "".join(["%02x" % (color * 255) for color in c])

    def is_light(self, color):
        """tells you if color is dark or light, so you can up or down the
        scale for improved contrast"""
        return colorsys.rgb_to_hls(*self.rgb(color))[1] > 150

    def darker(self, color, step):
        """returns color darker by step (where step is in range 0..255)"""
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

Colors = ColorUtils() # this is a static class, so an instance will do

def get_gdk_rectangle(x, y, w, h):
    rect = gdk.Rectangle()
    rect.x, rect.y, rect.width, rect.height = x or 0, y or 0, w or 0, h or 0
    return rect




def chain(*steps):
    """chains the given list of functions and object animations into a callback string.

        Expects an interlaced list of object and params, something like:
            object, {params},
            callable, {params},
            object, {},
            object, {params}
    Assumes that all callees accept on_complete named param.
    The last item in the list can omit that.
    XXX - figure out where to place these guys as they are quite useful
    """
    if not steps:
        return

    def on_done(sprite=None):
        chain(*steps[2:])

    obj, params = steps[:2]

    if len(steps) > 2:
        params['on_complete'] = on_done
    if callable(obj):
        obj(**params)
    else:
        obj.animate(**params)

def full_pixels(space, data, gap_pixels=1):
    """returns the given data distributed in the space ensuring it's full pixels
    and with the given gap.
    this will result in minor sub-pixel inaccuracies.
    XXX - figure out where to place these guys as they are quite useful
    """
    available = space - (len(data) - 1) * gap_pixels # 8 recs 7 gaps

    res = []
    for i, val in enumerate(data):
        # convert data to 0..1 scale so we deal with fractions
        data_sum = sum(data[i:])
        norm = val * 1.0 / data_sum


        w = max(int(round(available * norm)), 1)
        res.append(w)
        available -= w
    return res


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
    __slots__ = ('context', 'colors', 'extents', 'paths', '_last_matrix',
                 '__new_instructions', '__instruction_cache', 'cache_surface',
                 '_cache_layout')
    colors = Colors # pointer to the color utilities instance

    def __init__(self, context = None):
        self.context = context
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

    def stroke(self, color=None, alpha=1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("stroke")

    def fill(self, color = None, alpha = 1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("fill")

    def mask(self, pattern):
        self._add_instruction("mask", pattern)

    def stroke_preserve(self, color = None, alpha = 1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("stroke_preserve")

    def fill_preserve(self, color = None, alpha = 1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("fill_preserve")

    def new_path(self):
        self._add_instruction("new_path")

    def paint(self):
        self._add_instruction("paint")

    def set_font_face(self, face):
        self._add_instruction("set_font_face", face)

    def set_font_size(self, size):
        self._add_instruction("set_font_size", size)

    def set_source(self, image, x = 0, y = 0):
        self._add_instruction("set_source", image)

    def set_source_surface(self, surface, x = 0, y = 0):
        self._add_instruction("set_source_surface", surface, x, y)

    def set_source_pixbuf(self, pixbuf, x = 0, y = 0):
        self._add_instruction("set_source_pixbuf", pixbuf, x, y)

    def save_context(self):
        self._add_instruction("save")

    def restore_context(self):
        self._add_instruction("restore")

    def clip(self):
        self._add_instruction("clip")

    def rotate(self, radians):
        self._add_instruction("rotate", radians)

    def translate(self, x, y):
        self._add_instruction("translate", x, y)

    def scale(self, x_factor, y_factor):
        self._add_instruction("scale", x_factor, y_factor)

    def move_to(self, x, y):
        self._add_instruction("move_to", x, y)

    def line_to(self, x, y = None):
        if y is not None:
            self._add_instruction("line_to", x, y)
        elif isinstance(x, list) and y is None:
            for x2, y2 in x:
                self._add_instruction("line_to", x2, y2)


    def rel_line_to(self, x, y = None):
        if x is not None and y is not None:
            self._add_instruction("rel_line_to", x, y)
        elif isinstance(x, list) and y is None:
            for x2, y2 in x:
                self._add_instruction("rel_line_to", x2, y2)

    def curve_to(self, x, y, x2, y2, x3, y3):
        """draw a curve. (x2, y2) is the middle point of the curve"""
        self._add_instruction("curve_to", x, y, x2, y2, x3, y3)

    def close_path(self):
        self._add_instruction("close_path")

    def set_line_style(self, width = None, dash = None, dash_offset = 0):
        """change width and dash of a line"""
        if width is not None:
            self._add_instruction("set_line_width", width)

        if dash is not None:
            self._add_instruction("set_dash", dash, dash_offset)



    def _set_color(self, context, r, g, b, a):
        """the alpha has to changed based on the parent, so that happens at the
        time of drawing"""
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
        self._add_instruction("set_color", r, g, b, alpha)


    def arc(self, x, y, radius, start_angle, end_angle):
        """draw arc going counter-clockwise from start_angle to end_angle"""
        self._add_instruction("arc", x, y, radius, start_angle, end_angle)

    def circle(self, x, y, radius):
        """draw circle"""
        self._add_instruction("arc", x, y, radius, 0, math.pi * 2)

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

    def arc_negative(self, x, y, radius, start_angle, end_angle):
        """draw arc going clockwise from start_angle to end_angle"""
        self._add_instruction("arc_negative", x, y, radius, start_angle, end_angle)

    def triangle(self, x, y, width, height):
        self.move_to(x, y)
        self.line_to(width/2 + x, height + y)
        self.line_to(width + x, y)
        self.line_to(x, y)

    def rectangle(self, x, y, width, height, corner_radius = 0):
        """draw a rectangle. if corner_radius is specified, will draw
        rounded corners. corner_radius can be either a number or a tuple of
        four items to specify individually each corner, starting from top-left
        and going clockwise"""
        if corner_radius <= 0:
            self._add_instruction("rectangle", x, y, width, height)
            return

        # convert into 4 border and  make sure that w + h are larger than 2 * corner_radius
        if isinstance(corner_radius, (int, float)):
            corner_radius = [corner_radius] * 4
        corner_radius = [min(r, min(width, height) / 2) for r in corner_radius]

        x2, y2 = x + width, y + height
        self._rounded_rectangle(x, y, x2, y2, corner_radius)

    def _rounded_rectangle(self, x, y, x2, y2, corner_radius):
        if isinstance(corner_radius, (int, float)):
            corner_radius = [corner_radius] * 4

        self._add_instruction("move_to", x + corner_radius[0], y)
        self._add_instruction("line_to", x2 - corner_radius[1], y)
        self._add_instruction("curve_to", x2 - corner_radius[1] / 2, y, x2, y + corner_radius[1] / 2, x2, y + corner_radius[1])
        self._add_instruction("line_to", x2, y2 - corner_radius[2])
        self._add_instruction("curve_to", x2, y2 - corner_radius[2] / 2, x2 - corner_radius[2] / 2, y2, x2 - corner_radius[2], y2)
        self._add_instruction("line_to", x + corner_radius[3], y2)
        self._add_instruction("curve_to", x + corner_radius[3] / 2, y2, x, y2 - corner_radius[3] / 2, x, y2 - corner_radius[3])
        self._add_instruction("line_to", x, y + corner_radius[0])
        self._add_instruction("curve_to", x, y + corner_radius[0] / 2, x + corner_radius[0] / 2, y, x + corner_radius[0], y)

    def hexagon(self, x, y, height):
        side = height * 0.5
        angle_x = side * 0.5
        angle_y = side * 0.8660254
        self.move_to(x, y)
        self.line_to(x + side, y)
        self.line_to(x + side + angle_x, y + angle_y)
        self.line_to(x + side, y + 2*angle_y)
        self.line_to(x, y + 2*angle_y)
        self.line_to(x - angle_x, y + angle_y)
        self.line_to(x, y)
        self.close_path()

    def fill_area(self, x, y, width, height, color, opacity = 1):
        """fill rectangular area with specified color"""
        self.save_context()
        self.rectangle(x, y, width, height)
        self._add_instruction("clip")
        self.rectangle(x, y, width, height)
        self.fill(color, opacity)
        self.restore_context()

    def fill_stroke(self, fill = None, stroke = None, opacity = 1, line_width = None):
        """fill and stroke the drawn area in one go"""
        if line_width: self.set_line_style(line_width)

        if fill and stroke:
            self.fill_preserve(fill, opacity)
        elif fill:
            self.fill(fill, opacity)

        if stroke:
            self.stroke(stroke)

    def create_layout(self, size = None):
        """utility function to create layout with the default font. Size and
        alignment parameters are shortcuts to according functions of the
        pango.Layout"""
        if not self.context:
            # TODO - this is rather sloppy as far as exception goes
            #        should explain better
            raise "Can not create layout without existing context!"

        layout = pangocairo.create_layout(self.context)
        font_desc = pango.FontDescription(_font_desc)
        if size: font_desc.set_absolute_size(size * pango.SCALE)

        layout.set_font_description(font_desc)
        return layout

    def show_label(self, text, size = None, color = None, font_desc = None):
        """display text. unless font_desc is provided, will use system's default font"""
        font_desc = pango.FontDescription(font_desc or _font_desc)
        if color: self.set_color(color)
        if size: font_desc.set_absolute_size(size * pango.SCALE)
        self.show_layout(text, font_desc)

    def show_text(self, text):
        self._add_instruction("show_text", text)

    def text_path(self, text):
        """this function is most likely to change"""
        self._add_instruction("text_path", text)

    def _show_layout(self, context, layout, text, font_desc, alignment, width, wrap,
                     ellipsize, single_paragraph_mode):
        layout.set_font_description(font_desc)
        layout.set_markup(text)
        layout.set_width(int(width or -1))
        layout.set_single_paragraph_mode(single_paragraph_mode)
        if alignment is not None:
            layout.set_alignment(alignment)

        if width > 0:
            if wrap is not None:
                layout.set_wrap(wrap)
            else:
                layout.set_ellipsize(ellipsize or pango.EllipsizeMode.END)

        pangocairo.show_layout(context, layout)


    def show_layout(self, text, font_desc, alignment = pango.Alignment.LEFT,
                    width = -1, wrap = None, ellipsize = None,
                    single_paragraph_mode = False):
        """display text. font_desc is string of pango font description
           often handier than calling this function directly, is to create
           a class:Label object
        """
        layout = self._cache_layout = self._cache_layout or pangocairo.create_layout(cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0)))
        self._add_instruction("show_layout", layout, text, font_desc,
                              alignment, width, wrap, ellipsize, single_paragraph_mode)


    def _add_instruction(self, function, *params):
        if self.context:
            if function == "set_color":
                self._set_color(self.context, *params)
            elif function == "show_layout":
                self._show_layout(self.context, *params)
            else:
                getattr(self.context, function)(*params)
        else:
            self.paths = None
            self.__new_instructions.append((function, params))


    def _draw(self, context, opacity):
        """draw accumulated instructions in context"""

        # if we have been moved around, we should update bounds
        fresh_draw = len(self.__new_instructions or []) > 0
        if fresh_draw: #new stuff!
            self.paths = []
            self.__instruction_cache = self.__new_instructions
            self.__new_instructions = []
        else:
            if not self.__instruction_cache:
                return

        for instruction, args in self.__instruction_cache:
            if fresh_draw:
                if instruction in ("new_path", "stroke", "fill", "clip"):
                    self.paths.append((instruction, "path", context.copy_path()))

                elif instruction in ("save", "restore", "translate", "scale", "rotate"):
                    self.paths.append((instruction, "transform", args))

            if instruction == "set_color":
                self._set_color(context, args[0], args[1], args[2], args[3] * opacity)
            elif instruction == "show_layout":
                self._show_layout(context, *args)
            elif opacity < 1 and instruction == "paint":
                context.paint_with_alpha(opacity)
            else:
                getattr(context, instruction)(*args)



    def _draw_as_bitmap(self, context, opacity):
        """
            instead of caching paths, this function caches the whole drawn thing
            use cache_as_bitmap on sprite to enable this mode
        """
        matrix = context.get_matrix()
        matrix_changed = matrix != self._last_matrix
        new_instructions = self.__new_instructions is not None and len(self.__new_instructions) > 0

        if not new_instructions and not matrix_changed:
            context.save()
            context.identity_matrix()
            context.translate(self.extents.x, self.extents.y)
            context.set_source_surface(self.cache_surface)
            if opacity < 1:
                context.paint_with_alpha(opacity)
            else:
                context.paint()
            context.restore()
            return


        if new_instructions:
            self.__instruction_cache = list(self.__new_instructions)
            self.__new_instructions = deque()

        self.paths = []
        self.extents = None

        if not self.__instruction_cache:
            # no instructions - nothing to do
            return

        # instructions that end path
        path_end_instructions = ("new_path", "clip", "stroke", "fill", "stroke_preserve", "fill_preserve")

        # measure the path extents so we know the size of cache surface
        # also to save some time use the context to paint for the first time
        extents = gdk.Rectangle()
        for instruction, args in self.__instruction_cache:
            if instruction in path_end_instructions:
                self.paths.append((instruction, "path", context.copy_path()))
                exts = context.path_extents()
                exts = get_gdk_rectangle(int(exts[0]), int(exts[1]),
                                         int(exts[2]-exts[0]), int(exts[3]-exts[1]))
                if extents.width and extents.height:
                    extents = gdk.rectangle_union(extents, exts)
                else:
                    extents = exts
            elif instruction in ("save", "restore", "translate", "scale", "rotate"):
                self.paths.append((instruction, "transform", args))


            if instruction in ("set_source_pixbuf", "set_source_surface"):
                # draw a rectangle around the pathless instructions so that the extents are correct
                pixbuf = args[0]
                x = args[1] if len(args) > 1 else 0
                y = args[2] if len(args) > 2 else 0
                context.rectangle(x, y, pixbuf.get_width(), pixbuf.get_height())
                context.clip()

            if instruction == "paint" and opacity < 1:
                context.paint_with_alpha(opacity)
            elif instruction == "set_color":
                self._set_color(context, args[0], args[1], args[2], args[3] * opacity)
            elif instruction == "show_layout":
                self._show_layout(context, *args)
            else:
                getattr(context, instruction)(*args)


        # avoid re-caching if we have just moved
        just_transforms = new_instructions == False and \
                          matrix and self._last_matrix \
                          and all([matrix[i] == self._last_matrix[i] for i in range(4)])

        # TODO - this does not look awfully safe
        extents.x += matrix[4] - 5
        extents.y += matrix[5] - 5
        self.extents = extents

        if not just_transforms:
            # now draw the instructions on the caching surface
            w = int(extents.width) + 10
            h = int(extents.height) + 10
            self.cache_surface = context.get_target().create_similar(cairo.CONTENT_COLOR_ALPHA, w, h)
            ctx = cairo.Context(self.cache_surface)
            ctx.translate(-extents.x, -extents.y)

            ctx.transform(matrix)
            for instruction, args in self.__instruction_cache:
                if instruction == "set_color":
                    self._set_color(ctx, args[0], args[1], args[2], args[3])
                elif instruction == "show_layout":
                    self._show_layout(ctx, *args)
                else:
                    getattr(ctx, instruction)(*args)

        self._last_matrix = matrix


class Parent(object):
    """shared functions across scene and sprite"""

    def find(self, id):
        """breadth-first sprite search by ID"""
        for sprite in self.sprites:
            if sprite.id == id:
                return sprite

        for sprite in self.sprites:
            found = sprite.find(id)
            if found:
                return found

    def __getitem__(self, i):
        return self.sprites[i]

    def traverse(self, attr_name = None, attr_value = None):
        """traverse the whole sprite tree and return child sprites which have the
        attribute and it's set to the specified value.
        If falue is None, will return all sprites that have the attribute
        """
        for sprite in self.sprites:
            if (attr_name is None) or \
               (attr_value is None and hasattr(sprite, attr_name)) or \
               (attr_value is not None and getattr(sprite, attr_name, None) == attr_value):
                yield sprite

            for child in sprite.traverse(attr_name, attr_value):
                yield child

    def log(self, *lines):
        """will print out the lines in console if debug is enabled for the
           specific sprite"""
        if getattr(self, "debug", False):
            print dt.datetime.now().time(),
            for line in lines:
                print line,
            print

    def _add(self, sprite, index = None):
        """add one sprite at a time. used by add_child. split them up so that
        it would be possible specify the index externally"""
        if sprite == self:
            raise Exception("trying to add sprite to itself")

        if sprite.parent:
            sprite.x, sprite.y = self.from_scene_coords(*sprite.to_scene_coords())
            sprite.parent.remove_child(sprite)

        if index is not None:
            self.sprites.insert(index, sprite)
        else:
            self.sprites.append(sprite)
        sprite.parent = self


    def _sort(self):
        """sort sprites by z_order"""
        self.__dict__['_z_ordered_sprites'] = sorted(self.sprites, key=lambda sprite:sprite.z_order)

    def add_child(self, *sprites):
        """Add child sprite. Child will be nested within parent"""
        for sprite in sprites:
            self._add(sprite)
        self._sort()
        self.redraw()

    def remove_child(self, *sprites):
        """Remove one or several :class:`Sprite` sprites from scene """

        # first drop focus
        scene = self.get_scene()

        if scene:
            child_sprites = list(self.all_child_sprites())
            if scene._focus_sprite in child_sprites:
                scene._focus_sprite = None


        for sprite in sprites:
            if sprite in self.sprites:
                self.sprites.remove(sprite)
                sprite._scene = None
                sprite.parent = None
            self.disconnect_child(sprite)
        self._sort()
        self.redraw()


    def clear(self):
        """Remove all child sprites"""
        self.remove_child(*self.sprites)


    def destroy(self):
        """recursively removes all sprite children so that it is freed from
        any references and can be garbage collected"""
        for sprite in self.sprites:
            sprite.destroy()
        self.clear()


    def all_child_sprites(self):
        """returns all child and grandchild sprites in a flat list"""
        for sprite in self.sprites:
            for child_sprite in sprite.all_child_sprites():
                yield child_sprite
            yield sprite


    def get_mouse_sprites(self):
        """returns list of child sprites that the mouse can interact with.
        by default returns all visible sprites, but override
        to define your own rules"""
        return (sprite for sprite in self._z_ordered_sprites if sprite.visible)


    def connect_child(self, sprite, event, *args, **kwargs):
        """connect to a child event so that will disconnect if the child is
        removed from this sprite. this is the recommended way to connect to
        child events. syntax is same as for the .connect itself, just you
        prepend the child sprite as the first element"""
        handler = sprite.connect(event, *args, **kwargs)
        self._child_handlers[sprite].append(handler)
        return handler

    def connect_child_after(self, sprite, event, *args, **kwargs):
        """connect to a child event so that will disconnect if the child is
        removed from this sprite. this is the recommended way to connect to
        child events. syntax is same as for the .connect itself, just you
        prepend the child sprite as the first element"""
        handler = sprite.connect_after(event, *args, **kwargs)
        self._child_handlers[sprite].append(handler)
        return handler

    def disconnect_child(self, sprite, *handlers):
        """disconnects from child event. if handler is not specified, will
        disconnect from all the child sprite events"""
        handlers = handlers or self._child_handlers.get(sprite, [])
        for handler in list(handlers):
            if sprite.handler_is_connected(handler):
                sprite.disconnect(handler)
            if handler in self._child_handlers.get(sprite, []):
                self._child_handlers[sprite].remove(handler)

        if not self._child_handlers[sprite]:
            del self._child_handlers[sprite]

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, getattr(self, "id", None) or str(id(self)))


class Sprite(Parent, gobject.GObject):
    """The Sprite class is a basic display list building block: a display list
       node that can display graphics and can also contain children.
       Once you have created the sprite, use Scene's add_child to add it to
       scene
    """

    __gsignals__ = {
        "on-mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-mouse-move": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-out": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-mouse-down": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-double-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-triple-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-up": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-scroll": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag-start": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag-finish": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-focus": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-blur": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-key-press": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-key-release": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-render": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    transformation_attrs = set(('x', 'y', 'rotation', 'scale_x', 'scale_y', 'pivot_x', 'pivot_y'))

    visibility_attrs = set(('opacity', 'visible', 'z_order'))

    cache_attrs = set(('_stroke_context', '_matrix', '_prev_parent_matrix', '_scene'))

    graphics_unrelated_attrs = set(('drag_x', 'drag_y', 'sprites', 'mouse_cursor', '_sprite_dirty', 'id'))

    #: mouse-over cursor of the sprite. Can be either a gdk cursor
    #: constants, or a pixbuf or a pixmap. If set to False, will be using
    #: scene's cursor. in order to have the cursor displayed, the sprite has
    #: to be interactive
    mouse_cursor = None

    #: whether the widget can gain focus
    can_focus = None

    def __init__(self, x = 0, y = 0, opacity = 1, visible = True, rotation = 0,
                 pivot_x = 0, pivot_y = 0, scale_x = 1, scale_y = 1,
                 interactive = False, draggable = False, z_order = 0,
                 mouse_cursor = None, cache_as_bitmap = False,
                 snap_to_pixel = True, debug = False, id = None,
                 can_focus = False):
        gobject.GObject.__init__(self)

        # a place where to store child handlers
        self.__dict__['_child_handlers'] = defaultdict(list)

        self._scene = None

        self.debug = debug

        self.id = id

        #: list of children sprites. Use :func:`add_child` to add sprites
        self.sprites = []

        self._z_ordered_sprites = []

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

        #: focus state
        self.focused = False


        if mouse_cursor is not None:
            self.mouse_cursor = mouse_cursor

        if can_focus is not None:
            self.can_focus = can_focus



        self.__dict__["_sprite_dirty"] = True # flag that indicates that the graphics object of the sprite should be rendered

        self._matrix = None
        self._prev_parent_matrix = None

        self._stroke_context = None

        self.connect("on-click", self.__on_click)



    def __setattr__(self, name, val):
        if isinstance(getattr(type(self), name, None), property) and \
           getattr(type(self), name).fset is not None:
            getattr(type(self), name).fset(self, val)
            return

        prev = self.__dict__.get(name, "hamster_graphics_no_value_really")
        if type(prev) == type(val) and prev == val:
            return
        self.__dict__[name] = val

        # prev parent matrix walks downwards
        if name == '_prev_parent_matrix' and self.visible:
            # downwards recursive invalidation of parent matrix
            for sprite in self.sprites:
                sprite._prev_parent_matrix = None


        if name in self.cache_attrs or name in self.graphics_unrelated_attrs:
            return

        """all the other changes influence cache vars"""

        if name == 'visible' and self.visible == False:
            # when transforms happen while sprite is invisible
            for sprite in self.sprites:
                sprite._prev_parent_matrix = None


        # on moves invalidate our matrix, child extent cache (as that depends on our transforms)
        # as well as our parent's child extents as we moved
        # then go into children and invalidate the parent matrix down the tree
        if name in self.transformation_attrs:
            self._matrix = None
            for sprite in self.sprites:
                sprite._prev_parent_matrix = None
        elif name not in self.visibility_attrs:
            # if attribute is not in transformation nor visibility, we conclude
            # that it must be causing the sprite needs re-rendering
            self.__dict__["_sprite_dirty"] = True

        # on parent change invalidate the matrix
        if name == 'parent':
            self._prev_parent_matrix = None
            return

        if name == 'opacity' and getattr(self, "cache_as_bitmap", None) and hasattr(self, "graphics"):
            # invalidating cache for the bitmap version as that paints opacity in the image
            self.graphics._last_matrix = None

        if name == 'z_order' and getattr(self, "parent", None):
            self.parent._sort()


        self.redraw()


    def _get_mouse_cursor(self):
        """Determine mouse cursor.
        By default look for self.mouse_cursor is defined and take that.
        Otherwise use gdk.CursorType.FLEUR for draggable sprites and gdk.CursorType.HAND2 for
        interactive sprites. Defaults to scenes cursor.
        """
        if self.mouse_cursor is not None:
            return self.mouse_cursor
        elif self.interactive and self.draggable:
            return gdk.CursorType.FLEUR
        elif self.interactive:
            return gdk.CursorType.HAND2

    def bring_to_front(self):
        """adjusts sprite's z-order so that the sprite is on top of it's
        siblings"""
        if not self.parent:
            return
        self.z_order = self.parent._z_ordered_sprites[-1].z_order + 1

    def send_to_back(self):
        """adjusts sprite's z-order so that the sprite is behind it's
        siblings"""
        if not self.parent:
            return
        self.z_order = self.parent._z_ordered_sprites[0].z_order - 1

    def has_focus(self):
        """True if the sprite has the global input focus, False otherwise."""
        scene = self.get_scene()
        return scene and scene._focus_sprite == self

    def grab_focus(self):
        """grab window's focus. Keyboard and scroll events will be forwarded
        to the sprite who has the focus. Check the 'focused' property of sprite
        in the on-render event to decide how to render it (say, add an outline
        when focused=true)"""
        scene = self.get_scene()
        if scene and scene._focus_sprite != self:
            scene._focus_sprite = self

    def blur(self):
        """removes focus from the current element if it has it"""
        scene = self.get_scene()
        if scene and scene._focus_sprite == self:
            scene._focus_sprite = None

    def __on_click(self, sprite, event):
        if self.interactive and self.can_focus:
            self.grab_focus()

    def get_parents(self):
        """returns all the parent sprites up until scene"""
        res = []
        parent = self.parent
        while parent and isinstance(parent, Scene) == False:
            res.insert(0, parent)
            parent = parent.parent

        return res


    def get_extents(self):
        """measure the extents of the sprite's graphics."""
        if self._sprite_dirty:
            # redrawing merely because we need fresh extents of the sprite
            context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
            context.transform(self.get_matrix())
            self.emit("on-render")
            self.__dict__["_sprite_dirty"] = False
            self.graphics._draw(context, 1)


        if not self.graphics.paths:
            self.graphics._draw(cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0)), 1)

        if not self.graphics.paths:
            return None

        context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))

        # bit of a hack around the problem - looking for clip instructions in parent
        # so extents would not get out of it
        clip_extents = None
        for parent in self.get_parents():
            context.transform(parent.get_local_matrix())
            if parent.graphics.paths:
                clip_regions = []
                for instruction, type, path in parent.graphics.paths:
                    if instruction == "clip":
                        context.append_path(path)
                        context.save()
                        context.identity_matrix()

                        clip_regions.append(context.fill_extents())
                        context.restore()
                        context.new_path()
                    elif instruction == "restore" and clip_regions:
                        clip_regions.pop()

                for ext in clip_regions:
                    ext = get_gdk_rectangle(int(ext[0]), int(ext[1]), int(ext[2] - ext[0]), int(ext[3] - ext[1]))
                    intersect, clip_extents = gdk.rectangle_intersect((clip_extents or ext), ext)

        context.transform(self.get_local_matrix())

        for instruction, type, path in self.graphics.paths:
            if type == "path":
                context.append_path(path)
            else:
                getattr(context, instruction)(*path)

        context.identity_matrix()


        ext = context.path_extents()
        ext = get_gdk_rectangle(int(ext[0]), int(ext[1]),
                                int(ext[2] - ext[0]), int(ext[3] - ext[1]))
        if clip_extents:
            intersect, ext = gdk.rectangle_intersect(clip_extents, ext)

        if not ext.width and not ext.height:
            ext = None

        self.__dict__['_stroke_context'] = context

        return ext


    def check_hit(self, x, y):
        """check if the given coordinates are inside the sprite's fill or stroke path"""
        extents = self.get_extents()

        if not extents:
            return False

        if extents.x <= x <= extents.x + extents.width and extents.y <= y <= extents.y + extents.height:
            return self._stroke_context is None or self._stroke_context.in_fill(x, y)
        else:
            return False

    def get_scene(self):
        """returns class:`Scene` the sprite belongs to"""
        if self._scene is None:
            parent = getattr(self, "parent", None)
            if parent:
                self._scene = parent.get_scene()
        return self._scene

    def redraw(self):
        """queue redraw of the sprite. this function is called automatically
           whenever a sprite attribute changes. sprite changes that happen
           during scene redraw are ignored in order to avoid echoes.
           Call scene.redraw() explicitly if you need to redraw in these cases.
        """
        scene = self.get_scene()
        if scene:
            scene.redraw()

    def animate(self, duration = None, easing = None, on_complete = None,
                on_update = None, round = False, **kwargs):
        """Request parent Scene to Interpolate attributes using the internal tweener.
           Specify sprite's attributes that need changing.
           `duration` defaults to 0.4 seconds and `easing` to cubic in-out
           (for others see pytweener.Easing class).

           Example::
             # tween some_sprite to coordinates (50,100) using default duration and easing
             self.animate(x = 50, y = 100)
        """
        scene = self.get_scene()
        if scene:
            return scene.animate(self, duration, easing, on_complete,
                                 on_update, round, **kwargs)
        else:
            for key, val in kwargs.items():
                setattr(self, key, val)
            return None

    def stop_animation(self):
        """stop animation without firing on_complete"""
        scene = self.get_scene()
        if scene:
            scene.stop_animation(self)

    def get_local_matrix(self):
        if self._matrix is None:
            matrix, x, y, pivot_x, pivot_y = cairo.Matrix(), self.x, self.y, self.pivot_x, self.pivot_y

            if self.snap_to_pixel:
                matrix.translate(int(x) + int(pivot_x), int(y) + int(pivot_y))
            else:
                matrix.translate(x + pivot_x, self.y + pivot_y)

            if self.rotation:
                matrix.rotate(self.rotation)


            if self.snap_to_pixel:
                matrix.translate(int(-pivot_x), int(-pivot_y))
            else:
                matrix.translate(-pivot_x, -pivot_y)


            if self.scale_x != 1 or self.scale_y != 1:
                matrix.scale(self.scale_x, self.scale_y)

            self._matrix = matrix

        return cairo.Matrix() * self._matrix


    def get_matrix(self):
        """return sprite's current transformation matrix"""
        if self.parent:
            return self.get_local_matrix() * (self._prev_parent_matrix or self.parent.get_matrix())
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
            self.emit("on-render")
            self.__dict__["_sprite_dirty"] = False


        no_matrix = parent_matrix is None
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

        context.new_path() #forget about us

        if self.debug:
            exts = self.get_extents()
            if exts:
                debug_colors = ["#c17d11", "#73d216", "#3465a4",
                                "#75507b", "#cc0000", "#edd400", "#f57900"]
                depth = len(self.get_parents())
                color = debug_colors[depth % len(debug_colors)]
                context.save()
                context.identity_matrix()

                scene = self.get_scene()
                if scene:
                    # go figure - seems like the context we are given starts
                    # in window coords when calling identity matrix
                    scene_alloc = self.get_scene().get_allocation()
                    context.translate(scene_alloc.x, scene_alloc.y)


                context.rectangle(exts.x, exts.y, exts.width, exts.height)
                context.set_source_rgb(*Colors.parse(color))
                context.stroke()
                context.restore()

        for sprite in self._z_ordered_sprites:
            sprite._draw(context, self.opacity * opacity, matrix * parent_matrix)


        context.restore()

        # having parent and not being given parent matrix means that somebody
        # is calling draw directly - avoid caching matrix for such a case
        # because when we will get called properly it won't be respecting
        # the parent's transformations otherwise
        if isinstance(self.parent, Sprite) and no_matrix:
            self._prev_parent_matrix = None

    # using _do functions so that subclassees can override these
    def _do_mouse_down(self, event): self.emit("on-mouse-down", event)
    def _do_double_click(self, event): self.emit("on-double-click", event)
    def _do_triple_click(self, event): self.emit("on-triple-click", event)
    def _do_mouse_up(self, event): self.emit("on-mouse-up", event)
    def _do_click(self, event): self.emit("on-click", event)
    def _do_mouse_over(self): self.emit("on-mouse-over")
    def _do_mouse_move(self, event): self.emit("on-mouse-move", event)
    def _do_mouse_out(self): self.emit("on-mouse-out")
    def _do_focus(self): self.emit("on-focus")
    def _do_blur(self): self.emit("on-blur")
    def _do_key_press(self, event):
        self.emit("on-key-press", event)
        return False

    def _do_key_release(self, event):
        self.emit("on-key-release", event)
        return False


class BitmapSprite(Sprite):
    """Caches given image data in a surface similar to targets, which ensures
       that drawing it will be quick and low on CPU.
       Image data can be either :class:`cairo.ImageSurface` or :class:`GdkPixbuf.Pixbuf`
    """
    def __init__(self, image_data = None, cache_mode = None, **kwargs):
        Sprite.__init__(self, **kwargs)

        self.width, self.height = 0, 0
        self.cache_mode = cache_mode or cairo.CONTENT_COLOR_ALPHA
        #: image data
        self.image_data = image_data

        self._surface = None

        self.connect("on-render", self.on_render)


    def on_render(self, sprite):
        if not self._surface:
            self.graphics.rectangle(0, 0, self.width, self.height)
            self.graphics.new_path()

    def update_surface_cache(self):
        """for efficiency the image data is cached on a surface similar to the
        target one. so if you do custom drawing after setting the image data,
        it won't be reflected as the sprite has no idea about what is going on
        there. call this function to trigger cache refresh."""
        self._surface = None


    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        Sprite.__setattr__(self, name, val)
        if name == 'image_data':
            self._surface = None
            if self.image_data:
                self.__dict__['width'] = self.image_data.get_width()
                self.__dict__['height'] = self.image_data.get_height()

    def _draw(self, context, opacity = 1, parent_matrix = None):
        if self.image_data is None or self.width is None or self.height is None:
            return

        if not self._surface:
            # caching image on surface similar to the target
            surface = context.get_target().create_similar(self.cache_mode,
                                                          self.width,
                                                          self.height)

            local_context = cairo.Context(surface)
            if isinstance(self.image_data, GdkPixbuf.Pixbuf):
                gdk.cairo_set_source_pixbuf(local_context, self.image_data, 0, 0)
            else:
                local_context.set_source_surface(self.image_data)
            local_context.paint()

            # add instructions with the resulting surface
            self.graphics.clear()
            self.graphics.rectangle(0, 0, self.width, self.height)
            self.graphics.clip()
            self.graphics.set_source_surface(surface)
            self.graphics.paint()
            self.__dict__['_surface'] = surface


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
        self.theme = gtk.IconTheme.get_default()

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

    cache_attrs = Sprite.cache_attrs | set(("_letter_sizes", "__surface", "_ascent", "_bounds_width", "_measures"))

    def __init__(self, text = "", size = None, color = None,
                 alignment = pango.Alignment.LEFT, single_paragraph = False,
                 max_width = None, wrap = None, ellipsize = None, markup = "",
                 font_desc = None, **kwargs):
        Sprite.__init__(self, **kwargs)
        self.width, self.height = None, None


        self._test_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A8, 0, 0))
        self._test_layout = pangocairo.create_layout(self._test_context)


        #: absolute font size in pixels. this will execute set_absolute_size
        #: instead of set_size, which is fractional
        self.size = size

        #: pango.FontDescription, defaults to system font
        self.font_desc = pango.FontDescription(font_desc or _font_desc)

        #: color of label either as hex string or an (r,g,b) tuple
        self.color = color

        self._bounds_width = None

        #: wrapping method. Can be set to pango. [WRAP_WORD, WRAP_CHAR,
        #: WRAP_WORD_CHAR]
        self.wrap = wrap


        #: Ellipsize mode. Can be set to pango.[EllipsizeMode.NONE,
        #: EllipsizeMode.START, EllipsizeMode.MIDDLE, EllipsizeMode.END]
        self.ellipsize = ellipsize

        #: alignment. one of pango.[Alignment.LEFT, Alignment.RIGHT, Alignment.CENTER]
        self.alignment = alignment

        #: If setting is True, do not treat newlines and similar characters as
        #: paragraph separators; instead, keep all text in a single paragraph,
        #: and display a glyph for paragraph separator characters. Used when you
        #: want to allow editing of newlines on a single text line.
        #: Defaults to False
        self.single_paragraph = single_paragraph


        #: maximum  width of the label in pixels. if specified, the label
        #: will be wrapped or ellipsized depending on the wrap and ellpisize settings
        self.max_width = max_width

        self.__surface = None

        #: label text. upon setting will replace markup
        self.text = text

        #: label contents marked up using pango markup. upon setting will replace text
        self.markup = markup

        self._measures = {}

        self.connect("on-render", self.on_render)

        self.graphics_unrelated_attrs = self.graphics_unrelated_attrs | set(("__surface", "_bounds_width", "_measures"))

    def __setattr__(self, name, val):
        if name == "font_desc":
            if isinstance(val, basestring):
                val = pango.FontDescription(val)
            elif isinstance(val, pango.FontDescription):
                val = val.copy()

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


            if name in ("width", "text", "markup", "size", "font_desc", "wrap", "ellipsize", "max_width"):
                self._measures = {}
                # avoid chicken and egg
                if hasattr(self, "size") and (hasattr(self, "text") or hasattr(self, "markup")):
                    if self.size:
                        self.font_desc.set_absolute_size(self.size * pango.SCALE)
                    markup = getattr(self, "markup", "")
                    self.__dict__['width'], self.__dict__['height'] = self.measure(markup or getattr(self, "text", ""), escape = len(markup) == 0)



            if name == 'text':
                if val:
                    self.__dict__['markup'] = ""
                self.emit('on-change')
            elif name == 'markup':
                if val:
                    self.__dict__['text'] = ""
                self.emit('on-change')


    def measure(self, text, escape = True, max_width = None):
        """measures given text with label's font and size.
        returns width, height and ascent. Ascent's null in case if the label
        does not have font face specified (and is thusly using pango)"""

        if escape:
            text = text.replace ("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        if (max_width, text) in self._measures:
            return self._measures[(max_width, text)]

        width, height = None, None

        context = self._test_context

        layout = self._test_layout
        layout.set_font_description(self.font_desc)
        layout.set_markup(text)
        layout.set_single_paragraph_mode(self.single_paragraph)

        if self.alignment:
            layout.set_alignment(self.alignment)

        if self.wrap is not None:
            layout.set_wrap(self.wrap)
            layout.set_ellipsize(pango.EllipsizeMode.NONE)
        else:
            layout.set_ellipsize(self.ellipsize or pango.EllipsizeMode.END)

        if max_width is not None:
            layout.set_width(max_width * pango.SCALE)
        else:
            if self.max_width:
                max_width = self.max_width * pango.SCALE

            layout.set_width(int(self._bounds_width or max_width or -1))

        width, height = layout.get_pixel_size()

        self._measures[(max_width, text)] = width, height
        return self._measures[(max_width, text)]


    def on_render(self, sprite):
        if not self.text and not self.markup:
            self.graphics.clear()
            return

        self.graphics.set_color(self.color)

        rect_width = self.width

        max_width = 0
        if self.max_width:
            max_width = self.max_width * pango.SCALE

            # when max width is specified and we are told to align in center
            # do that (the pango instruction takes care of aligning within
            # the lines of the text)
            if self.alignment == pango.Alignment.CENTER:
                self.graphics.move_to(-(self.max_width - self.width)/2, 0)

        bounds_width = max_width or self._bounds_width or -1

        text = ""
        if self.markup:
            text = self.markup
        else:
            # otherwise escape pango
            text = self.text.replace ("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        self.graphics.show_layout(text, self.font_desc,
                                  self.alignment,
                                  bounds_width,
                                  self.wrap,
                                  self.ellipsize,
                                  self.single_paragraph)

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
        self.graphics.fill_stroke(self.fill, self.stroke, line_width = self.line_width)


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
        if not self.points:
            self.graphics.clear()
            return

        self.graphics.move_to(*self.points[0])
        self.graphics.line_to(self.points)

        if self.fill:
            self.graphics.close_path()

        self.graphics.fill_stroke(self.fill, self.stroke, line_width = self.line_width)


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

        self.graphics.fill_stroke(self.fill, self.stroke, line_width = self.line_width)


class Scene(Parent, gtk.DrawingArea):
    """ Drawing area for displaying sprites.
        Add sprites to the Scene by calling :func:`add_child`.
        Scene is descendant of `gtk.DrawingArea <http://www.pygtk.org/docs/pygtk/class-gtkdrawingarea.html>`_
        and thus inherits all it's methods and everything.
    """

    __gsignals__ = {
       # "draw": "override",
       # "configure_event": "override",
        "on-first-frame": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "on-enter-frame": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "on-finish-frame": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "on-resize": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),

        "on-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag-start": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag-finish": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),

        "on-mouse-move": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-down": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-double-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-triple-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-up": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-out": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-scroll": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),

        "on-key-press": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-key-release": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, interactive = True, framerate = 60,
                       background_color = None, scale = False, keep_aspect = True,
                       style_class=None):
        gtk.DrawingArea.__init__(self)

        self._style = self.get_style_context()

        #: widget style. One of gtk.STYLE_CLASS_*. By default it's BACKGROUND
        self.style_class = style_class or gtk.STYLE_CLASS_BACKGROUND
        self._style.add_class(self.style_class) # so we know our colors

        #: list of sprites in scene. use :func:`add_child` to add sprites
        self.sprites = []

        self._z_ordered_sprites = []

        # a place where to store child handlers
        self.__dict__['_child_handlers'] = defaultdict(list)

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
        self.tweener = False
        if pytweener:
            self.tweener = pytweener.Tweener(0.4, pytweener.Easing.Cubic.ease_in_out)

        #: instance of :class:`ColorUtils` class for color parsing
        self.colors = Colors

        #: read only info about current framerate (frames per second)
        self.fps = None # inner frames per second counter

        self._window = None # scenes don't really get reparented

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

        #: in contrast to the mouse cursor, this one is merely a suggestion and
        #: can be overidden by child sprites
        self.default_mouse_cursor = None

        self._blank_cursor = gdk.Cursor(gdk.CursorType.BLANK_CURSOR)

        self.__previous_mouse_signal_time = None


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

        #: When specified, upon window resize the content will be scaled
        #: relative to original window size. Defaults to False.
        self.scale = scale

        #: Should the stage maintain aspect ratio upon scale if
        #: :attr:`Scene.scale` is enabled. Defaults to true.
        self.keep_aspect = keep_aspect

        self._original_width, self._original_height = None,  None

        self._focus_sprite = None # our internal focus management

        self.__last_mouse_move = None

        if interactive:
            self.set_can_focus(True)
            self.set_events(gdk.EventMask.POINTER_MOTION_MASK
                            | gdk.EventMask.LEAVE_NOTIFY_MASK | gdk.EventMask.ENTER_NOTIFY_MASK
                            | gdk.EventMask.BUTTON_PRESS_MASK | gdk.EventMask.BUTTON_RELEASE_MASK
                            | gdk.EventMask.SCROLL_MASK
                            | gdk.EventMask.KEY_PRESS_MASK)
            self.connect("motion-notify-event", self.__on_mouse_move)
            self.connect("enter-notify-event", self.__on_mouse_enter)
            self.connect("leave-notify-event", self.__on_mouse_leave)
            self.connect("button-press-event", self.__on_button_press)
            self.connect("button-release-event", self.__on_button_release)
            self.connect("scroll-event", self.__on_scroll)
            self.connect("key-press-event", self.__on_key_press)
            self.connect("key-release-event", self.__on_key_release)



    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        if name == '_focus_sprite':
            prev_focus = getattr(self, '_focus_sprite', None)
            if prev_focus:
                prev_focus.focused = False
                self.__dict__['_focus_sprite'] = val # drop cache to avoid echoes
                prev_focus._do_blur()

            if val:
                val.focused = True
                val._do_focus()
        elif name == "style_class":
            if hasattr(self, "style_class"):
                self._style.remove_class(self.style_class)
            self._style.add_class(val)
        elif name == "background_color":
            if val:
                self.override_background_color(gtk.StateType.NORMAL,
                                               gdk.RGBA(*Colors.parse(val)))
            else:
                self.override_background_color(gtk.StateType.NORMAL, None)

        self.__dict__[name] = val

    # these two mimic sprite functions so parent check can be avoided
    def from_scene_coords(self, x, y): return x, y
    def to_scene_coords(self, x, y): return x, y
    def get_matrix(self): return cairo.Matrix()
    def get_scene(self): return self


    def animate(self, sprite, duration = None, easing = None, on_complete = None,
                on_update = None, round = False, **kwargs):
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
                                       round=round,
                                       **kwargs)
        self.redraw()
        return tween


    def stop_animation(self, sprites):
        """stop animation without firing on_complete"""
        if isinstance(sprites, list) is False:
            sprites = [sprites]

        for sprite in sprites:
            self.tweener.kill_tweens(sprite)


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


    def do_draw(self, context):
        if self.scale:
            aspect_x = self.width / self._original_width
            aspect_y = self.height / self._original_height
            if self.keep_aspect:
                aspect_x = aspect_y = min(aspect_x, aspect_y)
            context.scale(aspect_x, aspect_y)

        if self.fps is None:
            self._window = self.get_window()
            self.emit("on-first-frame", context)

        cursor, self.mouse_x, self.mouse_y, mods = self._window.get_pointer()


        # update tweens
        now = dt.datetime.now()
        delta = (now - (self._last_frame_time or dt.datetime.now())).total_seconds()
        self._last_frame_time = now
        if self.tweener:
            self.tweener.update(delta)

        self.fps = 1 / delta

        # start drawing
        self.emit("on-enter-frame", context)
        for sprite in self._z_ordered_sprites:
            sprite._draw(context)

        self.__check_mouse(self.mouse_x, self.mouse_y)
        self.emit("on-finish-frame", context)

        # reset the mouse signal time as redraw means we are good now
        self.__previous_mouse_signal_time = None


    def do_configure_event(self, event):
        if self._original_width is None:
            self._original_width = float(event.width)
            self._original_height = float(event.height)

        width, height = self.width, self.height
        self.width, self.height = event.width, event.height

        if width != event.width or height != event.height:
            self.emit("on-resize", event) # so that sprites can listen to it



    def all_mouse_sprites(self):
        """Returns flat list of the sprite tree for simplified iteration"""
        def all_recursive(sprites):
            if not sprites:
                return

            for sprite in sprites:
                if sprite.visible:
                    yield sprite

                    for child in all_recursive(sprite.get_mouse_sprites()):
                        yield child

        return all_recursive(self.get_mouse_sprites())


    def get_sprite_at_position(self, x, y):
        """Returns the topmost visible interactive sprite for given coordinates"""
        over = None
        for sprite in self.all_mouse_sprites():
            if sprite.interactive and sprite.check_hit(x, y):
                over = sprite

        return over


    def __check_mouse(self, x, y):
        if x is None or self._mouse_in == False:
            return

        cursor = None
        over = None

        if self.mouse_cursor is not None:
            cursor = self.mouse_cursor

        if cursor is None and self._drag_sprite:
            drag_cursor = self._drag_sprite._get_mouse_cursor()
            if drag_cursor:
                cursor = drag_cursor

        #check if we have a mouse over
        if self._drag_sprite is None:
            over = self.get_sprite_at_position(x, y)
            if self._mouse_sprite and self._mouse_sprite != over:
                self._mouse_sprite._do_mouse_out()
                self.emit("on-mouse-out", self._mouse_sprite)

            if over and cursor is None:
                sprite_cursor = over._get_mouse_cursor()
                if sprite_cursor:
                    cursor = sprite_cursor

            if over and over != self._mouse_sprite:
                over._do_mouse_over()
                self.emit("on-mouse-over", over)

            self._mouse_sprite = over

        if cursor is None:
            cursor = self.default_mouse_cursor or gdk.CursorType.ARROW # default
        elif cursor is False:
            cursor = self._blank_cursor

        if self.__last_cursor is None or cursor != self.__last_cursor:
            if isinstance(cursor, gdk.Cursor):
                self._window.set_cursor(cursor)
            else:
                self._window.set_cursor(gdk.Cursor(cursor))

            self.__last_cursor = cursor


    """ mouse events """
    def __on_mouse_move(self, scene, event):
        if self.__last_mouse_move:
            gobject.source_remove(self.__last_mouse_move)
            self.__last_mouse_move = None

        self.mouse_x, self.mouse_y = event.x, event.y

        # don't emit mouse move signals more often than every 0.05 seconds
        timeout = dt.timedelta(seconds=0.05)
        if self.__previous_mouse_signal_time and dt.datetime.now() - self.__previous_mouse_signal_time < timeout:
            self.__last_mouse_move = gobject.timeout_add((timeout - (dt.datetime.now() - self.__previous_mouse_signal_time)).microseconds / 1000,
                                                         self.__on_mouse_move,
                                                         scene,
                                                         event.copy())
            return

        state = event.state


        if self._mouse_down_sprite and self._mouse_down_sprite.interactive \
           and self._mouse_down_sprite.draggable and gdk.ModifierType.BUTTON1_MASK & event.state:
            # dragging around
            if not self.__drag_started:
                drag_started = (self.__drag_start_x is not None and \
                               (self.__drag_start_x - event.x) ** 2 + \
                               (self.__drag_start_y - event.y) ** 2 > self.drag_distance ** 2)

                if drag_started:
                    self._drag_sprite = self._mouse_down_sprite
                    self._mouse_down_sprite.emit("on-drag-start", event)
                    self.emit("on-drag-start", self._drag_sprite, event)
                    self.start_drag(self._drag_sprite, self.__drag_start_x, self.__drag_start_y)

        else:
            # avoid double mouse checks - the redraw will also check for mouse!
            if not self.__drawing_queued:
                self.__check_mouse(event.x, event.y)

        if self._drag_sprite:
            diff_x, diff_y = event.x - self.__drag_start_x, event.y - self.__drag_start_y
            if isinstance(self._drag_sprite.parent, Sprite):
                matrix = self._drag_sprite.parent.get_matrix()
                matrix.invert()
                diff_x, diff_y = matrix.transform_distance(diff_x, diff_y)

            self._drag_sprite.x, self._drag_sprite.y = self._drag_sprite.drag_x + diff_x, self._drag_sprite.drag_y + diff_y

            self._drag_sprite.emit("on-drag", event)
            self.emit("on-drag", self._drag_sprite, event)

        if self._mouse_sprite:
            sprite_event = event.copy()

            sprite_event.x, sprite_event.y = self._mouse_sprite.from_scene_coords(event.x, event.y)
            self._mouse_sprite._do_mouse_move(sprite_event)

        self.emit("on-mouse-move", event)
        self.__previous_mouse_signal_time = dt.datetime.now()


    def start_drag(self, sprite, cursor_x = None, cursor_y = None):
        """start dragging given sprite"""
        cursor_x, cursor_y = cursor_x or sprite.x, cursor_y or sprite.y

        self._mouse_down_sprite = self._drag_sprite = sprite
        sprite.drag_x, sprite.drag_y = self._drag_sprite.x, self._drag_sprite.y
        self.__drag_start_x, self.__drag_start_y = cursor_x, cursor_y
        self.__drag_started = True


    def __on_mouse_enter(self, scene, event):
        self._mouse_in = True

    def __on_mouse_leave(self, scene, event):
        self._mouse_in = False
        if self._mouse_sprite:
            self._mouse_sprite._do_mouse_out()
            self.emit("on-mouse-out", self._mouse_sprite)
            self._mouse_sprite = None


    def __on_button_press(self, scene, event):
        target = self.get_sprite_at_position(event.x, event.y)
        if not self.__drag_started:
            self.__drag_start_x, self.__drag_start_y = event.x, event.y

        self._mouse_down_sprite = target

        # differentiate between the click count!
        if event.type == gdk.EventType.BUTTON_PRESS:
            self.emit("on-mouse-down", event)
            if target:
                target_event = event.copy()
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_mouse_down(target_event)
            else:
                scene._focus_sprite = None  # lose focus if mouse ends up nowhere
        elif event.type == gdk.EventType._2BUTTON_PRESS:
            self.emit("on-double-click", event)
            if target:
                target_event = event.copy()
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_double_click(target_event)
        elif event.type == gdk.EventType._3BUTTON_PRESS:
            self.emit("on-triple-click", event)
            if target:
                target_event = event.copy()
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_triple_click(target_event)

        self.__check_mouse(event.x, event.y)
        return True


    def __on_button_release(self, scene, event):
        target = self.get_sprite_at_position(event.x, event.y)

        if target:
            target._do_mouse_up(event)
        self.emit("on-mouse-up", event)

        # trying to not emit click and drag-finish at the same time
        click = not self.__drag_started or (event.x - self.__drag_start_x) ** 2 + \
                                           (event.y - self.__drag_start_y) ** 2 < self.drag_distance
        if (click and self.__drag_started == False) or not self._drag_sprite:
            if target and target == self._mouse_down_sprite:
                target_event = event.copy()
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_click(target_event)

            self.emit("on-click", event, target)

        self._mouse_down_sprite = None
        self.__drag_started = False
        self.__drag_start_x, self__drag_start_y = None, None

        if self._drag_sprite:
            self._drag_sprite.drag_x, self._drag_sprite.drag_y = None, None
            drag_sprite, self._drag_sprite = self._drag_sprite, None
            drag_sprite.emit("on-drag-finish", event)
            self.emit("on-drag-finish", drag_sprite, event)
        self.__check_mouse(event.x, event.y)
        return True


    def __on_scroll(self, scene, event):
        target = self.get_sprite_at_position(event.x, event.y)
        if target:
            target.emit("on-mouse-scroll", event)
        self.emit("on-mouse-scroll", event)
        return True

    def __on_key_press(self, scene, event):
        handled = False
        if self._focus_sprite:
            handled = self._focus_sprite._do_key_press(event)
        if not handled:
            self.emit("on-key-press", event)
        return True

    def __on_key_release(self, scene, event):
        handled = False
        if self._focus_sprite:
            handled = self._focus_sprite._do_key_release(event)
        if not handled:
            self.emit("on-key-release", event)
        return True
