# - coding: utf-8 -

# Copyright (C) 2009 Toms Bauģis <toms.baugis at gmail.com>

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


import pygtk
pygtk.require('2.0')

import os
import gtk, gobject
from ..configuration import conf

class ReportChooserDialog(gtk.Dialog):
    __gsignals__ = {
        # format, path, start_date, end_date
        'report-chosen': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, gobject.TYPE_STRING)),
        'report-chooser-closed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }
    def __init__(self):
        gtk.Dialog.__init__(self)


        self.dialog = gtk.FileChooserDialog(title = _(u"Save Report — Time Tracker"),
                                            parent = self,
                                            action = gtk.FILE_CHOOSER_ACTION_SAVE,
                                            buttons=(gtk.STOCK_CANCEL,
                                                     gtk.RESPONSE_CANCEL,
                                                     gtk.STOCK_SAVE,
                                                     gtk.RESPONSE_OK))

        # try to set path to last known folder or fall back to home
        report_folder = os.path.expanduser(conf.get("last_report_folder"))
        if os.path.exists(report_folder):
            self.dialog.set_current_folder(report_folder)
        else:
            self.dialog.set_current_folder(os.path.expanduser("~"))

        self.filters = {}

        filter = gtk.FileFilter()
        filter.set_name(_("HTML Report"))
        filter.add_mime_type("text/html")
        filter.add_pattern("*.html")
        filter.add_pattern("*.htm")
        self.filters[filter] = "html"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("Tab-Separated Values (TSV)"))
        filter.add_mime_type("text/plain")
        filter.add_pattern("*.tsv")
        filter.add_pattern("*.txt")
        self.filters[filter] = "tsv"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("XML"))
        filter.add_mime_type("text/xml")
        filter.add_pattern("*.xml")
        self.filters[filter] = "xml"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name(_("iCal"))
        filter.add_mime_type("text/calendar")
        filter.add_pattern("*.ics")
        self.filters[filter] = "ical"
        self.dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        self.dialog.add_filter(filter)


    def show(self, start_date, end_date):
        """setting suggested name to something readable, replace backslashes
           with dots so the name is valid in linux"""

        # title in the report file name
        vars = {"title": _("Time track"),
                "start": start_date.strftime("%x").replace("/", "."),
                "end": end_date.strftime("%x").replace("/", ".")}
        if start_date != end_date:
            filename = "%(title)s, %(start)s - %(end)s.html" % vars
        else:
            filename = "%(title)s, %(start)s.html" % vars

        self.dialog.set_current_name(filename)

        response = self.dialog.run()

        if response != gtk.RESPONSE_OK:
            self.emit("report-chooser-closed")
            self.dialog.destroy()
            self.dialog = None
        else:
            self.on_save_button_clicked()


    def present(self):
        self.dialog.present()

    def on_save_button_clicked(self):
        path, format = None,  None

        format = "html"
        if self.dialog.get_filter() in self.filters:
            format = self.filters[self.dialog.get_filter()]
        path = self.dialog.get_filename()

        # append correct extension if it is missing
        # TODO - proper way would be to change extension on filter change
        # only pointer in web is http://www.mail-archive.com/pygtk@daa.com.au/msg08740.html
        if path.endswith(".%s" % format) == False:
            path = "%s.%s" % (path.rstrip("."), format)

        categories = []

        conf.set("last_report_folder", os.path.dirname(path))

        # format, path, start_date, end_date
        self.emit("report-chosen", format, path)
        self.dialog.destroy()
        self.dialog = None
