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

from .hamster import stuff
from .hamster.i18n import C_
from .hamster.configuration import runtime

from dateinput import DateInput

class ReportChooserDialog(gtk.Dialog):
    __gsignals__ = {
        # format, path, start_date, end_date
        'report-chosen': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, gobject.TYPE_STRING,
                           gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,
                           gobject.TYPE_PYOBJECT)),
        'report-chooser-closed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }
    def __init__(self):
        gtk.Dialog.__init__(self)
        ui = stuff.load_ui_file("stats_reports.ui")
        self.dialog = ui.get_object('save_report_dialog')

        self.dialog.set_action(gtk.FILE_CHOOSER_ACTION_SAVE)
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
        
        self.start_date = DateInput()
        ui.get_object('from_date_box').add(self.start_date)
        self.end_date = DateInput()
        ui.get_object('to_date_box').add(self.end_date)

        self.category_box = ui.get_object('category_box')

        ui.get_object('save_button').connect("clicked", self.on_save_button_clicked)
        ui.get_object('cancel_button').connect("clicked", self.on_cancel_button_clicked)
        

    def show(self, start_date, end_date):
        #set suggested name to something readable, replace backslashes with dots
        #so the name is valid in linux
        filename = "Time track %s - %s." % (start_date.strftime("%x").replace("/", "."),
                                           end_date.strftime("%x").replace("/", "."))
        self.dialog.set_current_name(filename)
        
        self.start_date.set_date(start_date)
        self.end_date.set_date(end_date)
        
        #add unsorted category
        button_all = gtk.CheckButton(C_("categories", "All").encode("utf-8"))
        button_all.value = None
        button_all.set_active(True)
        
        def on_category_all_clicked(checkbox):
            active = checkbox.get_active()
            for checkbox in self.category_box.get_children():
                checkbox.set_active(active)
        
        button_all.connect("clicked", on_category_all_clicked)
        self.category_box.attach(button_all, 0, 1, 0, 1)

        categories = runtime.storage.get_category_list()
        col, row = 0, 0
        for category in categories:
            col +=1
            if col % 4 == 0:
                col = 0
                row +=1

            button = gtk.CheckButton(category['name'].encode("utf-8"))
            button.value = category['id']
            button.set_active(True)
            self.category_box.attach(button, col, col+1, row, row+1)

        

        response = self.dialog.show_all()

    def present(self):
        self.dialog.present()

    def on_save_button_clicked(self, widget):
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
        for button in self.category_box.get_children():
            if button.get_active():
                categories.append(button.value)
        
        if None in categories:
            categories = None # nothing is everything
        
        # format, path, start_date, end_date
        self.emit("report-chosen", format, path,
                           self.start_date.get_date().date(),
                           self.end_date.get_date().date(),
                           categories)
        self.dialog.destroy()
        

    def on_cancel_button_clicked(self, widget):
        self.emit("report-chooser-closed")
        self.dialog.destroy()
