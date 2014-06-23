# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Copyright (c) 2014 Toms Baugis <toms.baugis@gmail.com>
# Dual licensed under the MIT or GPL Version 2 licenses.

import datetime as dt
import math
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import Pango as pango
from collections import defaultdict

import graphics


class Widget(graphics.Sprite):
    """Base class for all widgets. You can use the width and height attributes
    to request a specific width."""

    _sizing_attributes = set(("visible", "min_width", "min_height",
                              "expand", "fill", "spacing",
                              "horizontal_spacing", "vertical_spacing", "x_align",
                              "y_align"))

    min_width = None  #: minimum width of the widget
    min_height = None #: minimum height of the widget

    #: Whether the child should receive extra space when the parent grows.
    expand = True

    #: Whether extra space given to the child should be allocated to the
    #: child or used as padding. Edit :attr:`x_align` and
    #: :attr:`y_align` properties to adjust alignment when fill is set to False.
    fill = True

    #: horizontal alignment within the parent. Works when :attr:`fill` is False
    x_align = 0.5

    #: vertical alignment within the parent. Works when :attr:`fill` is False
    y_align = 0.5

    #: child padding - shorthand to manipulate padding in pixels ala CSS. tuple
    #: of one to four elements. Setting this value overwrites values of
    #: :attr:`padding_top`, :attr:`padding_right`, :attr:`padding_bottom`
    #: and :attr:`padding_left`
    padding = None
    padding_top = None    #: child padding - top
    padding_right = None  #: child padding - right
    padding_bottom = None #: child padding - bottom
    padding_left = None   #: child padding - left

    #: widget margins - shorthand to manipulate margin in pixels ala CSS. tuple
    #: of one to four elements. Setting this value overwrites values of
    #: :attr:`margin_top`, :attr:`margin_right`, :attr:`margin_bottom` and
    #: :attr:`margin_left`
    margin = 0
    margin_top = 0     #: top margin
    margin_right = 0   #: right margin
    margin_bottom = 0  #: bottom margin
    margin_left = 0    #: left margin

    enabled = True #: whether the widget is enabled

    mouse_cursor = False #: Mouse cursor. see :attr:`graphics.Sprite.mouse_cursor` for values

    def __init__(self, width = None, height = None, expand = None, fill = None,
                 x_align = None, y_align = None,
                 padding_top = None, padding_right = None,
                 padding_bottom = None, padding_left = None, padding = None,
                 margin_top = None, margin_right = None,
                 margin_bottom = None, margin_left = None, margin = None,
                 enabled = None, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)

        def set_if_not_none(name, val):
            # set values - avoid pitfalls of None vs 0/False
            if val is not None:
                setattr(self, name, val)

        set_if_not_none("min_width", width)
        set_if_not_none("min_height", height)

        self._enabled = enabled if enabled is not None else self.__class__.enabled

        set_if_not_none("fill", fill)
        set_if_not_none("expand", expand)
        set_if_not_none("x_align", x_align)
        set_if_not_none("y_align", y_align)

        # set padding
        # (class, subclass, instance, and constructor)
        if padding is not None or self.padding is not None:
            self.padding = padding if padding is not None else self.padding
        self.padding_top = padding_top or self.__class__.padding_top or self.padding_top or 0
        self.padding_right = padding_right or self.__class__.padding_right or self.padding_right or 0
        self.padding_bottom = padding_bottom or self.__class__.padding_bottom or self.padding_bottom or 0
        self.padding_left = padding_left or self.__class__.padding_left or self.padding_left or 0

        if margin is not None or self.margin is not None:
            self.margin = margin if margin is not None else self.margin
        self.margin_top = margin_top or self.__class__.margin_top or self.margin_top or 0
        self.margin_right = margin_right or self.__class__.margin_right or self.margin_right or 0
        self.margin_bottom = margin_bottom or self.__class__.margin_bottom or self.margin_bottom or 0
        self.margin_left = margin_left or self.__class__.margin_left or self.margin_left or 0


        #: width in pixels that have been allocated to the widget by parent
        self.alloc_w = width if width is not None else self.min_width

        #: height in pixels that have been allocated to the widget by parent
        self.alloc_h = height if height is not None else self.min_height

        self.connect_after("on-render", self.__on_render)
        self.connect("on-mouse-over", self.__on_mouse_over)
        self.connect("on-mouse-out", self.__on_mouse_out)
        self.connect("on-mouse-down", self.__on_mouse_down)
        self.connect("on-key-press", self.__on_key_press)

        self._children_resize_queued = True
        self._scene_resize_handler = None


    def __setattr__(self, name, val):
        # forward width and height to min_width and min_height as i've ruined the setters a bit i think
        if name == "width":
            name = "min_width"
        elif name == "height":
            name = "min_height"
        elif name == 'enabled':
            name = '_enabled'
        elif name == "padding":
            val = val or 0
            if isinstance(val, int):
                val = (val, )

            if len(val) == 1:
                self.padding_top = self.padding_right = self.padding_bottom = self.padding_left = val[0]
            elif len(val) == 2:
                self.padding_top = self.padding_bottom = val[0]
                self.padding_right = self.padding_left = val[1]

            elif len(val) == 3:
                self.padding_top = val[0]
                self.padding_right = self.padding_left = val[1]
                self.padding_bottom = val[2]
            elif len(val) == 4:
                self.padding_top, self.padding_right, self.padding_bottom, self.padding_left = val
            return

        elif name == "margin":
            val = val or 0
            if isinstance(val, int):
                val = (val, )

            if len(val) == 1:
                self.margin_top = self.margin_right = self.margin_bottom = self.margin_left = val[0]
            elif len(val) == 2:
                self.margin_top = self.margin_bottom = val[0]
                self.margin_right = self.margin_left = val[1]
            elif len(val) == 3:
                self.margin_top = val[0]
                self.margin_right = self.margin_left = val[1]
                self.margin_bottom = val[2]
            elif len(val) == 4:
                self.margin_top, self.margin_right, self.margin_bottom, self.margin_left = val
            return


        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        graphics.Sprite.__setattr__(self, name, val)

        # in widget case visibility affects placement and everything so request repositioning from parent
        if name == 'visible' and getattr(self, "parent", None) and getattr(self.parent, "resize_children", None):
            self.parent.resize_children()

        elif name == '_enabled' and getattr(self, "sprites", None):
            self._propagate_enabledness()

        if name in self._sizing_attributes:
            self.queue_resize()

    def _propagate_enabledness(self):
        # runs down the tree and marks all child sprites as dirty as
        # enabledness is inherited
        self._sprite_dirty = True
        for sprite in self.sprites:
            next_call = getattr(sprite, "_propagate_enabledness", None)
            if next_call:
                next_call()

    def _with_rotation(self, w, h):
        """calculate the actual dimensions after rotation"""
        res_w = abs(w * math.cos(self.rotation) + h * math.sin(self.rotation))
        res_h = abs(h * math.cos(self.rotation) + w * math.sin(self.rotation))
        return res_w, res_h

    @property
    def horizontal_padding(self):
        """total calculated horizontal padding. A read-only property."""
        return self.padding_left + self.padding_right

    @property
    def vertical_padding(self):
        """total calculated vertical padding.  A read-only property."""
        return self.padding_top + self.padding_bottom

    def __on_mouse_over(self, sprite):
        cursor, mouse_x, mouse_y, mods = sprite.get_scene().get_window().get_pointer()
        if self.tooltip and not gdk.ModifierType.BUTTON1_MASK & mods:
            self._set_tooltip(self.tooltip)


    def __on_mouse_out(self, sprite):
        if self.tooltip:
            self._set_tooltip(None)

    def __on_mouse_down(self, sprite, event):
        if self.can_focus:
            self.grab_focus()
        if self.tooltip:
            self._set_tooltip(None)

    def __on_key_press(self, sprite, event):
        if event.keyval in (gdk.KEY_Tab, gdk.KEY_ISO_Left_Tab):
            idx = self.parent.sprites.index(self)

            if event.state & gdk.ModifierType.SHIFT_MASK: # going backwards
                if idx > 0:
                    idx -= 1
                    self.parent.sprites[idx].grab_focus()
            else:
                if idx < len(self.parent.sprites) - 1:
                    idx += 1
                    self.parent.sprites[idx].grab_focus()


    def queue_resize(self):
        """request the element to re-check it's child sprite sizes"""
        self._children_resize_queued = True
        parent = getattr(self, "parent", None)
        if parent and isinstance(parent, graphics.Sprite) and hasattr(parent, "queue_resize"):
            parent.queue_resize()


    def get_min_size(self):
        """returns size required by the widget"""
        if self.visible == False:
            return 0, 0
        else:
            return ((self.min_width or 0) + self.horizontal_padding + self.margin_left + self.margin_right,
                    (self.min_height or 0) + self.vertical_padding + self.margin_top + self.margin_bottom)



    def insert(self, index = 0, *widgets):
        """insert widget in the sprites list at the given index.
        by default will prepend."""
        for widget in widgets:
            self._add(widget, index)
            index +=1 # as we are moving forwards
        self._sort()


    def insert_before(self, target):
        """insert this widget into the targets parent before the target"""
        if not target.parent:
            return
        target.parent.insert(target.parent.sprites.index(target), self)

    def insert_after(self, target):
        """insert this widget into the targets parent container after the target"""
        if not target.parent:
            return
        target.parent.insert(target.parent.sprites.index(target) + 1, self)


    @property
    def width(self):
        """width in pixels"""
        alloc_w = self.alloc_w

        if self.parent and isinstance(self.parent, graphics.Scene):
            alloc_w = self.parent.width

            def res(scene, event):
                if self.parent:
                    self.queue_resize()
                else:
                    scene.disconnect(self._scene_resize_handler)
                    self._scene_resize_handler = None


            if not self._scene_resize_handler:
                # TODO - disconnect on reparenting
                self._scene_resize_handler = self.parent.connect("on-resize", res)


        min_width = (self.min_width or 0) + self.margin_left + self.margin_right
        w = alloc_w if alloc_w is not None and self.fill else min_width
        w = max(w or 0, self.get_min_size()[0])
        return w - self.margin_left - self.margin_right

    @property
    def height(self):
        """height in pixels"""
        alloc_h = self.alloc_h

        if self.parent and isinstance(self.parent, graphics.Scene):
            alloc_h = self.parent.height

        min_height = (self.min_height or 0) + self.margin_top + self.margin_bottom
        h = alloc_h if alloc_h is not None and self.fill else min_height
        h = max(h or 0, self.get_min_size()[1])
        return h - self.margin_top - self.margin_bottom

    @property
    def enabled(self):
        """whether the user is allowed to interact with the
        widget. Item is enabled only if all it's parent elements are"""
        enabled = self._enabled
        if not enabled:
            return False

        if self.parent and isinstance(self.parent, Widget):
            if self.parent.enabled == False:
                return False

        return True


    def __on_render(self, sprite):
        self.do_render()
        if self.debug:
            self.graphics.save_context()

            w, h = self.width, self.height
            if hasattr(self, "get_height_for_width_size"):
                w2, h2 = self.get_height_for_width_size()
                w2 = w2 - self.margin_left - self.margin_right
                h2 = h2 - self.margin_top - self.margin_bottom
                w, h = max(w, w2), max(h, h2)

            self.graphics.rectangle(0.5, 0.5, w, h)
            self.graphics.set_line_style(3)
            self.graphics.stroke("#666", 0.5)
            self.graphics.restore_context()

            if self.pivot_x or self.pivot_y:
                self.graphics.fill_area(self.pivot_x - 3, self.pivot_y - 3, 6, 6, "#666")


    def do_render(self):
        """this function is called in the on-render event. override it to do
           any drawing. subscribing to the "on-render" event will work too, but
           overriding this method is preferred for easier subclassing.
        """
        pass





def get_min_size(sprite):
    if hasattr(sprite, "get_min_size"):
        min_width, min_height = sprite.get_min_size()
    else:
        min_width, min_height = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

    min_width = min_width * sprite.scale_x
    min_height = min_height * sprite.scale_y

    return min_width, min_height

def get_props(sprite):
    # gets all the relevant info for containers and puts it in a uniform dict.
    # this way we can access any object without having to check types and such
    keys = ("margin_top", "margin_right", "margin_bottom", "margin_left",
            "padding_top", "padding_right", "padding_bottom", "padding_left")
    res = dict((key, getattr(sprite, key, 0)) for key in keys)
    res["expand"] = getattr(sprite, "expand", True)

    return sprite, res


class Container(Widget):
    """The base container class that all other containers inherit from.
       You can insert any sprite in the container, just make sure that it either
       has width and height defined so that the container can do alignment, or
       for more sophisticated cases, make sure it has get_min_size function that
       returns how much space is needed.

       Normally while performing layout the container will update child sprites
       and set their alloc_h and alloc_w properties. The `alloc` part is short
       for allocated. So use that when making rendering decisions.
    """
    cache_attrs = Widget.cache_attrs | set(('_cached_w', '_cached_h'))
    _sizing_attributes = Widget._sizing_attributes | set(('padding_top', 'padding_right', 'padding_bottom', 'padding_left'))

    def __init__(self, contents = None, **kwargs):
        Widget.__init__(self, **kwargs)

        #: contents of the container - either a widget or a list of widgets
        self.contents = contents
        self._cached_w, self._cached_h = None, None


    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        Widget.__setattr__(self, name, val)
        if name == 'contents':
            if val:
                if isinstance(val, graphics.Sprite):
                    val = [val]
                self.add_child(*val)
            if self.sprites and self.sprites != val:
                self.remove_child(*list(set(self.sprites) ^ set(val or [])))

        if name in ("alloc_w", "alloc_h") and val:
            self.__dict__['_cached_w'], self.__dict__['_cached_h'] = None, None
            self._children_resize_queued = True


    @property
    def contents(self):
        return self.sprites


    def _Widget__on_render(self, sprite):
        if self._children_resize_queued:
            self.resize_children()
            self.__dict__['_children_resize_queued'] = False
        Widget._Widget__on_render(self, sprite)


    def _add(self, *sprites):
        Widget._add(self, *sprites)
        self.queue_resize()

    def remove_child(self, *sprites):
        Widget.remove_child(self, *sprites)
        self.queue_resize()

    def queue_resize(self):
        self.__dict__['_cached_w'], self.__dict__['_cached_h'] = None, None
        Widget.queue_resize(self)

    def get_min_size(self):
        # by default max between our requested size and the biggest child
        if self.visible == False:
            return 0, 0

        if self._cached_w is None:
            sprites = [sprite for sprite in self.sprites if sprite.visible]
            width = max([get_min_size(sprite)[0] for sprite in sprites] or [0])
            width += self.horizontal_padding  + self.margin_left + self.margin_right

            height = max([get_min_size(sprite)[1] for sprite in sprites] or [0])
            height += self.vertical_padding + self.margin_top + self.margin_bottom

            self._cached_w, self._cached_h = max(width, self.min_width or 0), max(height, self.min_height or 0)

        return self._cached_w, self._cached_h

    def get_height_for_width_size(self):
        return self.get_min_size()


    def resize_children(self):
        """default container alignment is to pile stuff just up, respecting only
        padding, margin and element's alignment properties"""
        width = self.width - self.horizontal_padding
        height = self.height - self.vertical_padding

        for sprite, props in (get_props(sprite) for sprite in self.sprites if sprite.visible):
            sprite.alloc_w = width
            sprite.alloc_h = height

            w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)
            if hasattr(sprite, "get_height_for_width_size"):
                w2, h2 = sprite.get_height_for_width_size()
                w, h = max(w, w2), max(h, h2)

            w = w * sprite.scale_x + props["margin_left"] + props["margin_right"]
            h = h * sprite.scale_y + props["margin_top"] + props["margin_bottom"]

            sprite.x = self.padding_left + props["margin_left"] + (max(sprite.alloc_w * sprite.scale_x, w) - w) * getattr(sprite, "x_align", 0)
            sprite.y = self.padding_top + props["margin_top"] + (max(sprite.alloc_h * sprite.scale_y, h) - h) * getattr(sprite, "y_align", 0)


        self.__dict__['_children_resize_queued'] = False


class Bin(Container):
    """A container with only one child. Adding new children will throw the
    previous ones out"""
    def __init__(self, contents = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

    @property
    def child(self):
        """child sprite. shorthand for self.sprites[0]"""
        return self.sprites[0] if self.sprites else None

    def get_height_for_width_size(self):
        if self._children_resize_queued:
            self.resize_children()

        sprites = [sprite for sprite in self.sprites if sprite.visible]
        width, height = 0, 0
        for sprite in sprites:
            if hasattr(sprite, "get_height_for_width_size"):
                w, h = sprite.get_height_for_width_size()
            else:
                w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

            w, h = w * sprite.scale_x, h * sprite.scale_y

            width = max(width, w)
            height = max(height, h)

        #width = width + self.horizontal_padding + self.margin_left + self.margin_right
        #height = height + self.vertical_padding + self.margin_top + self.margin_bottom

        return width, height


    def add_child(self, *sprites):
        if not sprites:
            return

        sprite = sprites[-1] # there can be just one

        # performing add then remove to not screw up coordinates in
        # a strange reparenting case
        Container.add_child(self, sprite)
        if self.sprites and self.sprites[0] != sprite:
            self.remove_child(*list(set(self.sprites) ^ set([sprite])))



class Fixed(Container):
    """Basic container that does not care about child positions. Handy if
       you want to place stuff yourself or do animations.
    """
    def __init__(self, contents = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

    def resize_children(self):
        # don't want
        pass



class Box(Container):
    """Align children either horizontally or vertically.
        Normally you would use :class:`HBox` or :class:`VBox` to be
        specific but this one is suited so you can change the packing direction
        dynamically.
    """
    #: spacing in pixels between children
    spacing = 5

    #: whether the box is packing children horizontally (from left to right) or vertically (from top to bottom)
    orient_horizontal = True

    def __init__(self, contents = None, horizontal = None, spacing = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

        if horizontal is not None:
            self.orient_horizontal = horizontal

        if spacing is not None:
            self.spacing = spacing

    def get_total_spacing(self):
        # now lay them out
        padding_sprites = 0
        for sprite in self.sprites:
            if sprite.visible:
                if getattr(sprite, "expand", True):
                    padding_sprites += 1
                else:
                    if hasattr(sprite, "get_min_size"):
                        size = sprite.get_min_size()[0] if self.orient_horizontal else sprite.get_min_size()[1]
                    else:
                        size = getattr(sprite, "width", 0) * sprite.scale_x if self.orient_horizontal else getattr(sprite, "height", 0) * sprite.scale_y

                    if size > 0:
                        padding_sprites +=1
        return self.spacing * max(padding_sprites - 1, 0)


    def resize_children(self):
        if not self.parent:
            return

        width = self.width - self.padding_left - self.padding_right
        height = self.height - self.padding_top - self.padding_bottom

        sprites = [get_props(sprite) for sprite in self.sprites if sprite.visible]

        # calculate if we have any spare space
        sprite_sizes = []
        for sprite, props in sprites:
            if self.orient_horizontal:
                sprite.alloc_h = height / sprite.scale_y
                size = get_min_size(sprite)[0]
                size = size + props["margin_left"] + props["margin_right"]
            else:
                sprite.alloc_w = width / sprite.scale_x
                size = get_min_size(sprite)[1]
                if hasattr(sprite, "get_height_for_width_size"):
                    size = max(size, sprite.get_height_for_width_size()[1] * sprite.scale_y)
                size = size + props["margin_top"] + props["margin_bottom"]
            sprite_sizes.append(size)


        remaining_space = width if self.orient_horizontal else height
        if sprite_sizes:
            remaining_space = remaining_space - sum(sprite_sizes) - self.get_total_spacing()


        interested_sprites = [sprite for sprite, props in sprites if getattr(sprite, "expand", True)]


        # in order to stay pixel sharp we will recalculate remaining bonus
        # each time we give up some of the remaining space
        remaining_interested = len(interested_sprites)
        bonus = 0
        if remaining_space > 0 and interested_sprites:
            bonus = int(remaining_space / remaining_interested)

        actual_h = 0
        x_pos, y_pos = 0, 0

        for (sprite, props), min_size in zip(sprites, sprite_sizes):
            sprite_bonus = 0
            if sprite in interested_sprites:
                sprite_bonus = bonus
                remaining_interested -= 1
                remaining_space -= bonus
                if remaining_interested:
                    bonus = int(float(remaining_space) / remaining_interested)


            if self.orient_horizontal:
                sprite.alloc_w = (min_size + sprite_bonus) / sprite.scale_x
            else:
                sprite.alloc_h = (min_size + sprite_bonus) / sprite.scale_y

            w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)
            if hasattr(sprite, "get_height_for_width_size"):
                w2, h2 = sprite.get_height_for_width_size()
                w, h = max(w, w2), max(h, h2)

            w = w * sprite.scale_x + props["margin_left"] + props["margin_right"]
            h = h * sprite.scale_y + props["margin_top"] + props["margin_bottom"]


            sprite.x = self.padding_left + x_pos + props["margin_left"] + (max(sprite.alloc_w * sprite.scale_x, w) - w) * getattr(sprite, "x_align", 0.5)
            sprite.y = self.padding_top + y_pos + props["margin_top"] + (max(sprite.alloc_h * sprite.scale_y, h) - h) * getattr(sprite, "y_align", 0.5)


            actual_h = max(actual_h, h * sprite.scale_y)

            if (min_size + sprite_bonus) > 0:
                if self.orient_horizontal:
                    x_pos += int(max(w, sprite.alloc_w * sprite.scale_x)) + self.spacing
                else:
                    y_pos += max(h, sprite.alloc_h * sprite.scale_y) + self.spacing


        if self.orient_horizontal:
            for sprite, props in sprites:
                sprite.__dict__['alloc_h'] = actual_h

        self.__dict__['_children_resize_queued'] = False

    def get_height_for_width_size(self):
        if self._children_resize_queued:
            self.resize_children()

        sprites = [sprite for sprite in self.sprites if sprite.visible]
        width, height = 0, 0
        for sprite in sprites:
            if hasattr(sprite, "get_height_for_width_size"):
                w, h = sprite.get_height_for_width_size()
            else:
                w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

            w, h = w * sprite.scale_x, h * sprite.scale_y


            if self.orient_horizontal:
                width += w
                height = max(height, h)
            else:
                width = max(width, w)
                height = height + h

        if self.orient_horizontal:
            width = width + self.get_total_spacing()
        else:
            height = height + self.get_total_spacing()

        width = width + self.horizontal_padding + self.margin_left + self.margin_right
        height = height + self.vertical_padding + self.margin_top + self.margin_bottom

        return width, height



    def get_min_size(self):
        if self.visible == False:
            return 0, 0

        if self._cached_w is None:
            sprites = [sprite for sprite in self.sprites if sprite.visible]

            width, height = 0, 0
            for sprite in sprites:
                if hasattr(sprite, "get_min_size"):
                    w, h = sprite.get_min_size()
                else:
                    w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

                w, h = w * sprite.scale_x, h * sprite.scale_y

                if self.orient_horizontal:
                    width += w
                    height = max(height, h)
                else:
                    width = max(width, w)
                    height = height + h

            if self.orient_horizontal:
                width = width + self.get_total_spacing()
            else:
                height = height + self.get_total_spacing()

            width = width + self.horizontal_padding + self.margin_left + self.margin_right
            height = height + self.vertical_padding + self.margin_top + self.margin_bottom

            w, h = max(width, self.min_width or 0), max(height, self.min_height or 0)
            self._cached_w, self._cached_h = w, h

        return self._cached_w, self._cached_h


class HBox(Box):
    """A horizontally aligned box. identical to ui.Box(horizontal=True)"""
    def __init__(self, contents = None, **kwargs):
        Box.__init__(self, contents, **kwargs)
        self.orient_horizontal = True


class VBox(Box):
    """A vertically aligned box. identical to ui.Box(horizontal=False)"""
    def __init__(self, contents = None, **kwargs):
        Box.__init__(self, contents, **kwargs)
        self.orient_horizontal = False



class _DisplayLabel(graphics.Label):
    cache_attrs = Box.cache_attrs | set(('_cached_w', '_cached_h'))

    def __init__(self, text="", **kwargs):
        graphics.Label.__init__(self, text, **kwargs)
        self._cached_w, self._cached_h = None, None
        self._cached_wh_w, self._cached_wh_h = None, None

    def __setattr__(self, name, val):
        graphics.Label.__setattr__(self, name, val)

        if name in ("text", "markup", "size", "wrap", "ellipsize", "max_width"):
            if name != "max_width":
                self._cached_w, self._cached_h = None, None
            self._cached_wh_w, self._cached_wh_h = None, None


    def get_min_size(self):
        if self._cached_w:
            return self._cached_w, self._cached_h

        text = self.markup or self.text
        escape = len(self.markup) == 0

        if self.wrap is not None or self.ellipsize is not None:
            self._cached_w = self.measure(text, escape, 1)[0]
            self._cached_h = self.measure(text, escape, -1)[1]
        else:
            self._cached_w, self._cached_h = self.measure(text, escape, -1)
        return self._cached_w, self._cached_h

    def get_height_for_width_size(self):
        if self._cached_wh_w:
            return self._cached_wh_w, self._cached_wh_h

        text = self.markup or self.text
        escape = len(self.markup) == 0
        self._cached_wh_w, self._cached_wh_h = self.measure(text, escape, self.max_width)

        return self._cached_wh_w, self._cached_wh_h


class Label(Bin):
    """a widget that displays a limited amount of read-only text"""
    #: pango.FontDescription to use for the label
    font_desc = None

    #: image attachment. one of top, right, bottom, left
    image_position = "left"

    #: font size
    size = None

    fill = False
    padding = 0
    x_align = 0.5

    def __init__(self, text = "", markup = "", spacing = 5, image = None,
                 image_position = None, size = None, font_desc = None,
                 overflow = False, color = "#000", background_color = None,
                 **kwargs):

        # TODO - am initiating table with fill = false but that yields suboptimal label placement and the 0,0 points to whatever parent gave us
        Bin.__init__(self, **kwargs)

        #: image to put next to the label
        self.image = image

        # the actual container that contains the label and/or image
        self.container = Box(spacing = spacing, fill = False,
                             x_align = self.x_align, y_align = self.y_align)

        if image_position is not None:
            self.image_position = image_position

        self.display_label = _DisplayLabel(text = text, markup = markup, color=color, size = size)
        self.display_label.x_align = 0 # the default is 0.5 which makes label align incorrectly on wrapping

        if font_desc or self.font_desc:
            self.display_label.font_desc = font_desc or self.font_desc

        self.display_label.size = size or self.size

        self.background_color = background_color

        #: either the pango `wrap <http://www.pygtk.org/pygtk2reference/pango-constants.html#pango-wrap-mode-constants>`_
        #: or `ellipsize <http://www.pygtk.org/pygtk2reference/pango-constants.html#pango-ellipsize-mode-constants>`_ constant.
        #: if set to False will refuse to become smaller
        self.overflow = overflow

        self.add_child(self.container)

        self._position_contents()
        self.connect_after("on-render", self.__on_render)

    def get_mouse_sprites(self):
        return None

    @property
    def text(self):
        """label text. This attribute and :attr:`markup` are mutually exclusive."""
        return self.display_label.text

    @property
    def markup(self):
        """pango markup to use in the label.
        This attribute and :attr:`text` are mutually exclusive."""
        return self.display_label.markup

    @property
    def color(self):
        """label color"""
        return self.display_label.color

    def __setattr__(self, name, val):
        if name in ("text", "markup", "color", "size"):
            if self.display_label.__dict__.get(name, "hamster_graphics_no_value_really") == val:
                return
            setattr(self.display_label, name, val)
        elif name in ("spacing"):
            setattr(self.container, name, val)
        else:
            if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
                return
            Bin.__setattr__(self, name, val)


        if name in ('x_align', 'y_align') and hasattr(self, "container"):
            setattr(self.container, name, val)

        elif name == "alloc_w" and hasattr(self, "display_label") and getattr(self, "overflow") is not False:
            self._update_max_width()

        elif name == "min_width" and hasattr(self, "display_label"):
            self.display_label.width = val - self.horizontal_padding

        elif name == "overflow" and hasattr(self, "display_label"):
            if val is False:
                self.display_label.wrap = None
                self.display_label.ellipsize = None
            elif isinstance(val, pango.WrapMode) and val in (pango.WrapMode.WORD, pango.WrapMode.WORD_CHAR, pango.WrapMode.CHAR):
                self.display_label.wrap = val
                self.display_label.ellipsize = None
            elif isinstance(val, pango.EllipsizeMode) and val in (pango.EllipsizeMode.START, pango.EllipsizeMode.MIDDLE, pango.EllipsizeMode.END):
                self.display_label.wrap = None
                self.display_label.ellipsize = val

            self._update_max_width()
        elif name in ("font_desc", "size"):
            setattr(self.display_label, name, val)

        if name in ("text", "markup", "image", "image_position", "overflow", "size"):
            if hasattr(self, "overflow"):
                self._position_contents()
                self.container.queue_resize()


    def _update_max_width(self):
        # updates labels max width, respecting image and spacing
        if self.overflow is False:
            self.display_label.max_width = -1
        else:
            w = (self.alloc_w or 0) - self.horizontal_padding - self.container.spacing
            if self.image and self.image_position in ("left", "right"):
                w -= self.image.width - self.container.spacing
            self.display_label.max_width = w

        self.container.queue_resize()


    def _position_contents(self):
        if self.image and (self.text or self.markup):
            self.image.expand = False
            self.container.orient_horizontal = self.image_position in ("left", "right")

            if self.image_position in ("top", "left"):
                if self.container.sprites != [self.image, self.display_label]:
                    self.container.clear()
                    self.container.add_child(self.image, self.display_label)
            else:
                if self.container.sprites != [self.display_label, self.image]:
                    self.container.clear()
                    self.container.add_child(self.display_label, self.image)
        elif self.image or (self.text or self.markup):
            sprite = self.image or self.display_label
            if self.container.sprites != [sprite]:
                self.container.clear()
                self.container.add_child(sprite)


    def __on_render(self, sprite):
        w, h = self.width, self.height
        w2, h2 = self.get_height_for_width_size()
        w, h = max(w, w2), max(h, h2)
        self.graphics.rectangle(0, 0, w, h)

        if self.background_color:
            self.graphics.fill(self.background_color)
        else:
            self.graphics.new_path()
