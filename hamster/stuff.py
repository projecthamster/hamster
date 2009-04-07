# - coding: utf-8 -

# Copyright (C) 2008 Toms Bauģis <toms.baugis at gmail.com>

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


# some widgets that repeat all over the place
# cells, columns, trees and other

import gtk
from hamster import storage, SHARED_DATA_DIR
import pango
from pango import ELLIPSIZE_END

import datetime as dt
import locale
import os

def load_ui_file(name):
    ui = gtk.Builder()
    ui.add_from_file(os.path.join(SHARED_DATA_DIR, name))
    return ui 

def zero_hour(date):
    return dt.datetime.combine(date.date(), dt.time(0,0))
    
# it seems that python or something has bug of sorts, that breaks stuff for
# japanese locale, so we have this locale from and to ut8 magic in some places
# see bug 562298
def locale_from_utf8(utf8_str):
    try:
        retval = unicode (utf8_str, "utf-8").encode(locale.getpreferredencoding())
    except:
        retval = utf8_str
    return retval

def locale_to_utf8(locale_str):
    try:
        retval = unicode (locale_str, locale.getpreferredencoding()).encode("utf-8")
    except:
        retval = locale_str
    return retval

class CategoryCell(gtk.CellRendererText):
    def __init__(self):
        gtk.CellRendererText.__init__(self)        
        self.set_property('alignment', pango.ALIGN_RIGHT)
        
        insensitive_color = gtk.Label().style.fg[gtk.STATE_INSENSITIVE]
        self.set_property('foreground-gdk', insensitive_color)
        self.set_property('scale', pango.SCALE_SMALL)
        self.set_property('yalign', 0.0)


insensitive_color = gtk.Label().style.fg[gtk.STATE_INSENSITIVE].to_string()
def format_activity(name, category, description, pad_description = False):
    "returns pango markup for activity with category and description"
    text = name    
    if category and category != _("Unsorted"):
        text += """ - <span color="%s" size="x-small">%s</span>""" % (insensitive_color, category)

    if description:
        text+= "\n"
        if pad_description:
            text += "          "

        text += """<span style="italic" size="small">%s</span>""" % description
        
    return text
    

class ActivityColumn(gtk.TreeViewColumn):
    def activity_painter(self, column, cell, model, iter):
        activity_name = model.get_value(iter, self.name)
        description = model.get_value(iter, self.description)
        category = model.get_value(iter, self.category)
        
        markup = format_activity(activity_name, category, description)            
        cell.set_property('markup', markup)
        return
        
    def __init__(self, name, description, category = None):
        gtk.TreeViewColumn.__init__(self)
        
        self.name, self.description, self.category = name, description, category
        self.set_expand(True)
        cell = gtk.CellRendererText()
        self.pack_start(cell, True)
        cell.set_property("ellipsize", pango.ELLIPSIZE_END)
        self.set_cell_data_func(cell, self.activity_painter)

def format_duration(minutes, human = True):
    if not minutes:
        if human:
            return ""
        else:
            return "00:00"
    
    hours = minutes / 60
    minutes = minutes % 60
    formatted_duration = ""
    
    if human:
        if minutes % 60 == 0:
            # duration in round hours
            formatted_duration += _("%dh") % (hours)
        elif hours == 0:
            # duration less than hour
            formatted_duration += _("%dmin") % (minutes % 60.0)
        else:
            # x hours, y minutes
            formatted_duration += _("%dh %dmin") % (hours, minutes % 60)
    else:
        formatted_duration += "%02d:%02d" % (hours, minutes)
    
    
    return formatted_duration

def dateDict(date, prefix):
    """converts date into dictionary, having prefix for all the keys"""
    res = {}
    
    res[prefix+"a"] = date.strftime("%a")
    res[prefix+"A"] = date.strftime("%A")
    res[prefix+"b"] = date.strftime("%b")
    res[prefix+"B"] = date.strftime("%B")
    res[prefix+"c"] = date.strftime("%c")
    res[prefix+"d"] = date.strftime("%d")
    res[prefix+"H"] = date.strftime("%H")
    res[prefix+"I"] = date.strftime("%I")
    res[prefix+"j"] = date.strftime("%j")
    res[prefix+"m"] = date.strftime("%m")
    res[prefix+"M"] = date.strftime("%M")
    res[prefix+"p"] = date.strftime("%p")
    res[prefix+"S"] = date.strftime("%S")
    res[prefix+"U"] = date.strftime("%U")
    res[prefix+"w"] = date.strftime("%w")
    res[prefix+"W"] = date.strftime("%W")
    res[prefix+"x"] = date.strftime("%x")
    res[prefix+"X"] = date.strftime("%X")
    res[prefix+"y"] = date.strftime("%y")
    res[prefix+"Y"] = date.strftime("%Y")
    res[prefix+"Z"] = date.strftime("%Z")
    
    for i, value in res.items():
        res[i] = locale_to_utf8(value)

    return res

def escape_pango(text):
    if not text:
        return text
    
    text = text.replace ("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text
