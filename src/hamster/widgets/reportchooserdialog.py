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


import os
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Gio as gio
from hamster.lib.configuration import conf


class ReportChooserDialog(gobject.GObject):
    __gsignals__ = {
        # format, path
        'report-chosen': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, gobject.TYPE_STRING)),
        'report-chooser-closed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self):
        gobject.GObject.__init__(self)
        self._dialog = None
        self._filters = {}

    def show(self, start_date, end_date):
        """Create and show the file save dialog with a suggested filename.

        Setting suggested name to something readable, replace backslashes
        with dots so the name is valid in linux.
        """
        dialog = gtk.FileDialog()
        dialog.set_title(_("Save Report — Time Tracker"))

        # Try to set path to last known folder or fall back to home
        report_folder = os.path.expanduser(conf.get("last-report-folder"))
        if os.path.exists(report_folder):
            dialog.set_initial_folder(gio.File.new_for_path(report_folder))
        else:
            dialog.set_initial_folder(gio.File.new_for_path(os.path.expanduser("~")))

        # Set suggested filename
        start = start_date.strftime("%Y-%m-%d")
        if start_date != end_date:
            end = end_date.strftime("%Y-%m-%d")
            filename = "Time track {} - {}.html".format(start, end)
        else:
            filename = "Time track {}.html".format(start)

        dialog.set_initial_name(filename)

        # Create filters
        filter_list = gio.ListStore.new(gtk.FileFilter)

        filters = {}
        for name, mime, patterns, key in [
            (_("HTML Report"), "text/html", ["*.html", "*.htm"], "html"),
            (_("Tab-Separated Values (TSV)"), "text/plain", ["*.tsv", "*.txt"], "tsv"),
            (_("XML"), "text/xml", ["*.xml"], "xml"),
            (_("iCal"), "text/calendar", ["*.ics"], "ical"),
        ]:
            f = gtk.FileFilter()
            f.set_name(name)
            f.add_mime_type(mime)
            for p in patterns:
                f.add_pattern(p)
            filters[f] = key
            filter_list.append(f)

        all_filter = gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        filter_list.append(all_filter)

        dialog.set_filters(filter_list)
        self._filters = filters
        self._dialog = dialog

        # Save async
        dialog.save(None, None, self._on_save_response)

    def _on_save_response(self, dialog, result):
        """Handle the async response from the file save dialog."""
        try:
            file = dialog.save_finish(result)
        except Exception:
            # User cancelled or error occurred
            self.emit("report-chooser-closed")
            return

        path = file.get_path()

        # Determine format from the selected filter
        format = "html"
        current_filter = self._dialog.get_default_filter()
        if current_filter in self._filters:
            format = self._filters[current_filter]

        # Append correct extension if it is missing
        # TODO - proper way would be to change extension on filter change
        # only pointer in web is http://www.mail-archive.com/pygtk@daa.com.au/msg08740.html
        if not path.endswith(".%s" % format):
            path = "%s.%s" % (path.rstrip("."), format)

        conf.set("last-report-folder", os.path.dirname(path))

        # format, path
        self.emit("report-chosen", format, path)
