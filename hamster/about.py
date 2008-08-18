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
from hamster import SHARED_DATA_DIR
from hamster.defs import VERSION
import gtk, gnomevfs
import hamster


def on_email(about, mail):
    gnomevfs.url_show("mailto:%s" % mail)

def on_url(about, link):
    gnomevfs.url_show(link)

gtk.about_dialog_set_email_hook(on_email)
gtk.about_dialog_set_url_hook(on_url)

def show_about(parent):
    about = gtk.AboutDialog()
    infos = {
        "name" : _("Time Tracker"),
        "version" : VERSION,
        "comments" : _("Time tracking for masses."),
        "copyright" : _("Copyright © 2007-2008 Toms Baugis and others"),
	"website" : "http://live.gnome.org/ProjectHamster",
        "website-label" : _("Hamster Website"),
    }

    about.set_authors(["Toms Baugis <toms.baugis@gmail.com>",
                       "Patryk Zawadzki <patrys@pld-linux.org>",
                       "Peteris Caune <cuu508@gmail.com>",
		       "Juanje Ojeda <jojeda@emergya.es>"])
    about.set_artists(["Kalle Persson <kalle@kallepersson.se>"])

    about.set_translator_credits(_("translator-credits"))

    for prop, val in infos.items():
        about.set_property(prop, val)

    hamster_logo = join(SHARED_DATA_DIR, 'art', 'hamster-applet.png')
        
    zupa = gtk.gdk.pixbuf_new_from_file(hamster_logo)
    about.set_logo(zupa)

    about.connect("response", lambda self, *args: self.destroy())
    about.set_screen(parent.get_screen())
    about.show_all()

