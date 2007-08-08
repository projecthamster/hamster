# -*- coding: utf-8 -*-
from os.path import join
from gettext import gettext as _
from hamster.defs import *
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
        "name" : _("Hamster"),
        "version" : VERSION,
        "comments" : _("Time tracking for masses."),
        "copyright" : "Copyright © 2007 Toms Baugis.",
        "website" : "http://projecthamster.wordpress.com/",
        "website-label" : _("Hamster Website"),
    }

    about.set_authors(["Toms Baugis <toms.baugis@gmail.com>"])
#    about.set_artists([])
#    about.set_documenters([])

    #translators: These appear in the About dialog, usual format applies.
    #about.set_translator_credits( _("translator-credits") )

    for prop, val in infos.items():
        about.set_property(prop, val)


    hamster_logo = join(DATA_DIR, "hamster-applet", 'art', 'tm.png')
        
    zupa = gtk.gdk.pixbuf_new_from_file(hamster_logo)
    about.set_logo(zupa)

    about.connect("response", lambda self, *args: self.destroy())
    about.set_screen(parent.get_screen())
    about.show_all()
    
    
