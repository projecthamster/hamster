# -*- coding: utf-8 -*-

# Copyright (C) 2007, 2008 Toms Bauģis <toms.baugis at gmail.com>

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


from os.path import join
from defs import VERSION
import gtk

def on_email(about, mail):
    gtk.show_uri(gtk.gdk.Screen(), "mailto:%s" % mail, 0L)

def on_url(about, link):
    gtk.show_uri(gtk.gdk.Screen(), link, 0L)

gtk.about_dialog_set_email_hook(on_email)
gtk.about_dialog_set_url_hook(on_url)

def show_about(parent):
    about = gtk.AboutDialog()
    infos = {
        "program-name" : _("Time Tracker"),
        "name" : _("Time Tracker"), #this should be deprecated in gtk 2.10
        "version" : VERSION,
        "comments" : _("Project Hamster — track your time"),
        "copyright" : _(u"Copyright © 2007–2009 Toms Bauģis and others"),
        "website" : "http://live.gnome.org/ProjectHamster",
        "website-label" : _("Project Hamster Website"),
        "title": _("About Time Tracker"),
        "wrap-license": True
    }
    
    about.set_authors(["Toms Bauģis <toms.baugis@gmail.com>",
                       "Patryk Zawadzki <patrys@pld-linux.org>",
                       "Pēteris Caune <cuu508@gmail.com>",
                       "Juanje Ojeda <jojeda@emergya.es>"])
    about.set_artists(["Kalle Persson <kalle@kallepersson.se>"])
    
    about.set_translator_credits(_("translator-credits"))

    for prop, val in infos.items():
        about.set_property(prop, val)

    about.set_logo_icon_name("hamster-applet")
    
    def on_destroy():
        parent.about = None

    about.connect("response", lambda self, *args: self.destroy())
    about.connect("destroy", lambda self, *args: on_destroy())
    about.set_screen(parent.get_screen())
    about.show_all()
    parent.about = about

