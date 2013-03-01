# coding: utf-8
#from hamster indicator
import gconf
import os.path
import appindicator
import gtk
import datetime as dt
import gobject
from hamster.lib import stuff
from hamster.configuration import dialogs, runtime

class ProjectHamsterStatusIcon():#gtk.StatusIcon):
    BASE_KEY = "/apps/hamster-indicator"
    def __init__(self, project):
        self.project = project

        # Gconf settings
        self._settings = gconf.client_get_default()
        self._settings.add_dir(self.BASE_KEY, gconf.CLIENT_PRELOAD_NONE)
        # Key to enable/disable icon glow
        self._icon_glow_path = os.path.join(self.BASE_KEY, "icon_glow")
        self._use_icon_glow = self._settings.get_bool(self._icon_glow_path)
        self._settings.notify_add(self._icon_glow_path, self._on_icon_glow_changed)

        # Key to show/hide the indicator label
        self._show_label_path = os.path.join(self.BASE_KEY, "show_label")
        self._show_label = self._settings.get_bool(self._show_label_path)
        self._settings.notify_add(self._show_label_path, self._on_show_label_changed)

        # Key to set the length of indicator label
        self._label_length_path = os.path.join(self.BASE_KEY, "label_length")
        self._label_length = self._settings.get_int(self._label_length_path)
        self._settings.notify_add(self._label_length_path, self._on_label_length_changed)

        self._activity_as_attribute = None
        # Create a fake applet since HamsterApplet requires one
#        applet = FakeApplet()

        self.indicator = appindicator.Indicator ("hamster-applet",
                                  "hamster-applet-inactive",
                                  appindicator.CATEGORY_SYSTEM_SERVICES)

        self.indicator.set_status (appindicator.STATUS_ACTIVE)
        # Set the attention icon as per the icon_glow gconf key
        self._set_attention_icon()

        # Initialise the activity label with "No Activity"
        self.indicator.set_label(self._get_no_activity_label())

        self.activity, self.duration = None, None

        self.menu = gtk.Menu()
        self.activity_item = gtk.MenuItem("")
        self.menu.append(self.activity_item)
        # this is where you would connect your menu item up with a function:
        self.activity_item.connect("activate", self.on_activate)
        self.activity_label = self.activity_item.get_child()
        self.activity_label.connect('style-set', self.on_label_style_set)

        # show the items
        self.activity_item.show()

        self.stop_activity_item = gtk.MenuItem(_(u"Sto_p Tracking"))
        self.menu.append(self.stop_activity_item)
        # this is where you would connect your menu item up with a function:
        self.stop_activity_item.connect("activate", self.on_stop_activity_activated, None)
        # show the items
        self.stop_activity_item.show()

        self.append_separator(self.menu)

        self.earlier_activity_item = gtk.MenuItem(_(u"Add earlier activity"))
        self.menu.append(self.earlier_activity_item)
        # this is where you would connect your menu item up with a function:
        self.earlier_activity_item.connect("activate", self.on_earlier_activity_activated, None)
        # show the items
        self.earlier_activity_item.show()

        self.overview_show_item = gtk.MenuItem(_(u"Show _Overview"))
        self.menu.append(self.overview_show_item)
        # this is where you would connect your menu item up with a function:
        self.overview_show_item.connect("activate", self.on_overview_show_activated, None)
        # show the items
        self.overview_show_item.show()

        self.append_separator(self.menu)

        self.preferences_show_item = gtk.MenuItem(_(u"Preferences"))
        self.menu.append(self.preferences_show_item)
        # this is where you would connect your menu item up with a function:
        self.preferences_show_item.connect("activate", self.on_show_preferences_activated, None)
        # show the items
        self.preferences_show_item.show()

        self.append_separator(self.menu)

        self.quit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        self.menu.append(self.quit_item)
        # this is where you would connect your menu item up with a function:
        self.quit_item.connect("activate", gtk.main_quit, None)
        # show the items
        self.quit_item.show()
        
        self.project.last_activity = None
        self.todays_facts = None
        runtime.storage.connect('activities-changed', self.after_activity_update)
        runtime.storage.connect('facts-changed', self.after_fact_update)
        runtime.storage.connect('toggle-called', self.on_toggle_called)
        
        gobject.timeout_add_seconds(20, self.refresh_tray) # refresh hamster every 60 seconds to update duration

    def on_activate(self, data):
        self.project.toggle_hamster_window()

    def on_quit(self, data):
        gtk.main_quit()
        
    def _on_show_label_changed(self, client, connection_id, entry, *args):
        '''Hide or show the indicator's label'''
        self._show_label = self._settings.get_bool(self._show_label_path)
        if self._show_label:
            self.update_label()
        else:
            self.indicator.set_label("")

    def _on_label_length_changed(self, client, connection_id, entry, *args):
        '''Resize the indicator's label'''
        self._label_length = self._settings.get_int(self._label_length_path)
        if self._show_label:
            self.update_label()
            
    def _set_attention_icon(self):
        '''Set the attention icon as per the gconf key'''
        if self._use_icon_glow:
            self.indicator.set_attention_icon('hamster-applet-active')
        else:
            self.indicator.set_attention_icon('hamster-applet-inactive')

    def _get_no_activity_label(self):
        '''Get the indicator label set to "No activity"'''
        return self._clamp_text(_(u"No activity"),
                                length=self._label_length,
                                with_ellipsis=False)

    def _clamp_text(self, text, length=25, with_ellipsis=True, is_indicator=False):
        text = stuff.escape_pango(text)
        if len(text) > length:  #ellipsize at some random length
            if with_ellipsis:
                if is_indicator:
                    text = "%s%s" % (text[:length], "...")
                else:
                    text = "%s%s" % (text[:length], "…")
            else:
                text = "%s" % (text[:length])
        return text
            
    def _on_icon_glow_changed(self, client, connection_id, entry, *args):
        self._use_icon_glow = self._settings.get_bool(self.BASE_KEY + "/icon_glow")
        self._set_attention_icon()

    def on_label_style_set(self, widget, something):
        self.reformat_label()

    def on_stop_activity_activated(self, *args):
        self.project.on_stop_tracking_clicked(None)

    def append_separator(self, menu):
        '''Add separator to the menu'''
        separator = gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

    def on_earlier_activity_activated(self, *args):
        dialogs.edit.show(self.indicator)

    def on_overview_show_activated(self, *args):
        dialogs.overview.show(self.indicator)

    def on_show_preferences_activated(self, *args):
        dialogs.prefs.show(self.indicator)
        
    def update_label(self):
        '''Override for menu items sensitivity and to update the menu'''
        if self.project.last_activity:
            # Let's see if activity is an attribute and cache the result.
            # This is only required for backwards compatibility
            if self._activity_as_attribute == None:
                self._activity_as_attribute = hasattr(self.project.last_activity,
                                                      'activity')
            if self._activity_as_attribute:
                start_time = self.project.last_activity.start_time
                end_time = self.project.last_activity.end_time
                last_activity_name = self.project.last_activity.activity
            else:
                start_time = self.project.last_activity['start_time']
                end_time = self.project.last_activity['end_time']
                last_activity_name = self.project.last_activity['name']

        if self.project.last_activity and end_time is None:
            self._set_activity_status(1)
            delta = dt.datetime.now() - start_time
            duration = delta.seconds /  60
            label = "%s %s" % (last_activity_name,
                               stuff.format_duration(duration, False))
            self.set_activity_text(last_activity_name,
                                 stuff.format_duration(duration, False))
            indicator_label = "%s %s" % (self._clamp_text(self.activity,
                                         length=self._label_length,
                                         with_ellipsis=False),
                                         self.duration)
        else:
            self._set_activity_status(0)
            label = "%s" % _(u"New activity")
            self.set_activity_text(label, None)
            indicator_label = self._get_no_activity_label()

        # Update the indicator label, if needed
        if self._show_label:
            self.indicator.set_label(indicator_label)
        else:
            self.indicator.set_label("")

        # Update the menu or the new activity text won't show up
        self.refresh_menu()

    def _set_activity_status(self, is_active):
        if is_active:
            # There's an active task
            self.indicator.set_status (appindicator.STATUS_ATTENTION)
        else:
            # There's no active task
            self.indicator.set_status (appindicator.STATUS_ACTIVE)
        self.stop_activity_item.set_sensitive(is_active)

    def set_activity_text(self, activity, duration):
        '''This adds a method which belongs to hamster.applet.PanelButton'''
#        activity = stuff.escape_pango(activity)
#        if len(activity) > 25:  #ellipsize at some random length
#            activity = "%s%s" % (activity[:25], "&#8230;")
        activity = self._clamp_text(activity, self._label_length)

        self.activity = activity
        self.duration = duration
        self.reformat_label()
        
    def reformat_label(self):
        '''This adds a method which belongs to hamster.applet.PanelButton'''
        label = self.activity
        if self.duration:
            label = "%s %s" % (self.activity, self.duration)
        label = '<span gravity="south">%s</span>' % label
        if self.activity_label:
            self.activity_label.set_markup("") #clear - seems to fix the warning
            self.activity_label.set_markup(label)

    def refresh_menu(self):
        '''Update the menu so that the new activity text is visible'''
        self.indicator.set_menu(self.menu)

    def show_indicator(self):
        self.indicator.set_menu(self.menu)
        self.refresh_tray()

    def refresh_tray(self):
        """refresh hamster every x secs - load today, check last activity etc."""
        self.update_label()
        return True

    """signals"""
    def after_activity_update(self, widget):
#        self.new_name.refresh_activities()
        self.project.load_day()
        self.update_label()

    def after_fact_update(self, event):
        self.project.load_day()
        self.update_label()
        
    def on_toggle_called(self, client):
#        self.__show_toggle(not self.button.get_active())
        pass
