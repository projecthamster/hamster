# coding: utf-8
#from hamster indicator
import gconf
import os.path
import gtk
import datetime as dt
import gobject
import locale
from hamster.lib import Fact, stuff
from hamster.configuration import dialogs, runtime, conf

have_appindicator = True
try:
    import appindicator
except:
    have_appindicator = False

    
def get_status_icon(project):
    if have_appindicator:
        return ProjectHamsterStatusIconUnity(project)
    else:
        return ProjectHamsterStatusIconGnome(project)

class ProjectHamsterStatusIconGnome(gtk.StatusIcon):
    def __init__(self, project):
        gtk.StatusIcon.__init__(self)

        self.project = project

        menu = '''
            <ui>
             <menubar name="Menubar">
              <menu action="Menu">
               <separator/>
               <menuitem action="Quit"/>
              </menu>
             </menubar>
            </ui>
        '''
        actions = [
            ('Menu',  None, 'Menu'),
            ('Quit', gtk.STOCK_QUIT, '_Quit...', None, 'Quit Time Tracker', self.on_quit)]
        ag = gtk.ActionGroup('Actions')
        ag.add_actions(actions)
        self.manager = gtk.UIManager()
        self.manager.insert_action_group(ag, 0)
        self.manager.add_ui_from_string(menu)
        self.menu = self.manager.get_widget('/Menubar/Menu/Quit').props.parent

        self.set_from_icon_name("hamster-time-tracker")
        self.set_name(_('Time Tracker'))

        self.connect('activate', self.on_activate)
        self.connect('popup-menu', self.on_popup_menu)

    def on_activate(self, data):
        self.project.toggle_hamster_window()

    def on_popup_menu(self, status, button, time):
        self.menu.popup(None, None, None, button, time)

    def on_quit(self, data):
        gtk.main_quit()
        
    def show(self):
        # show the status tray icon
        activity = self.project.get_widget("last_activity_name").get_text()
        self.set_tooltip(activity)
        self.set_visible(True)


class ProjectHamsterStatusIconUnity():
    BASE_KEY = "/apps/hamster-time-tracker"
    def __init__(self, project):
        self.project = project

        # Gconf settings
#        self._settings = gconf.client_get_default()
#        self._settings.add_dir(self.BASE_KEY, gconf.CLIENT_PRELOAD_NONE)
        # Key to enable/disable icon glow
        self._use_icon_glow = conf.get("icon_glow")
        self._show_label = conf.get("show_label")
        self._label_length = conf.get("label_length")
        self._last_activities_size = conf.get("last_activities_size")
        conf.connect('conf-changed', self.on_conf_changed)

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

        self.stop_activity_item = gtk.MenuItem(_(u"Sto_p tracking"))
        self.menu.append(self.stop_activity_item)
        # this is where you would connect your menu item up with a function:
        self.stop_activity_item.connect("activate", self.on_stop_activity_activated, None)
        # show the items
        self.stop_activity_item.show()
        
        self.last_activities_item = gtk.MenuItem(_(u"_Last activities"))
        self.menu.append(self.last_activities_item)
        # show the items
        self.last_activities_item.show()

        self.append_separator(self.menu)

        self.earlier_activity_item = gtk.MenuItem(_(u"Add earlier activity"))
        self.menu.append(self.earlier_activity_item)
        # this is where you would connect your menu item up with a function:
        self.earlier_activity_item.connect("activate", self.on_earlier_activity_activated, None)
        # show the items
        self.earlier_activity_item.show()

        self.overview_show_item = gtk.MenuItem(_(u"Show Overview"))
        self.menu.append(self.overview_show_item)
        # this is where you would connect your menu item up with a function:
        self.overview_show_item.connect("activate", self.on_overview_show_activated, None)
        # show the items
        self.overview_show_item.show()

        self.append_separator(self.menu)

        self.preferences_show_item = gtk.MenuItem(_(u"_Preferences"))
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
        runtime.storage.connect('activities-changed', self.after_activity_update)
        runtime.storage.connect('facts-changed', self.after_fact_update)
        runtime.storage.connect('toggle-called', self.on_toggle_called)
        
        gobject.timeout_add_seconds(20, self.refresh_tray) # refresh hamster every 20 seconds to update duration
    
    def on_conf_changed(self, event, key, value):
        self._on_icon_glow_changed()
        self._on_show_label_changed()
        self._on_label_length_changed()
        self._on_last_activities_size_changed()
    
    def on_activate(self, data):
        self.project.show_hamster_window()

    def on_quit(self, data):
        gtk.main_quit()
        
    def _on_show_label_changed(self):
        '''Hide or show the indicator's label'''
        self._show_label = conf.get("show_label")
        if self._show_label:
            self.update_label()
            self.update_last_activities()
        else:
            self.indicator.set_label("")

    def _on_label_length_changed(self):
        '''Resize the indicator's label'''
        self._label_length = conf.get("label_length")
        if self._show_label:
            self.update_label()

    def _on_last_activities_size_changed(self):
        self._last_activities_size = conf.get("last_activities_size")
        self.update_last_activities()
            
    def _set_attention_icon(self):
        '''Set the attention icon as per the gconf key'''
        if self._use_icon_glow:
            self.indicator.set_attention_icon('hamster-applet-active')
        else:
            self.indicator.set_attention_icon('hamster-applet-inactive')

    def _get_no_activity_label(self, today_duration=None):
        '''Get the indicator label set to "No activity"'''
        label = self._clamp_text(_(u"No activity"),
                                length=self._label_length,
                                with_ellipsis=False)
        if today_duration:
            label = "%s (%sh)" % (label, today_duration)
        return label

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
            
    def _on_icon_glow_changed(self):
        self._use_icon_glow = conf.get("icon_glow")
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
        
    def update_last_activities(self):
        date = dt.datetime.now() - dt.timedelta(days=365)
        last_facts = runtime.storage.get_facts(date = date, end_date = dt.datetime.now(), limit = self._last_activities_size+1, asc_by_date = False)
        self.last_activities_menu = gtk.Menu()
        if last_facts:
            self.last_activities_item.set_sensitive(True)
            self.last_activities_item.set_submenu(self.last_activities_menu)
            for fact in last_facts[:self._last_activities_size]:
                if fact.end_time:
                    time = fact.start_time.strftime("%d.%m %H:%M")
                    fact_name = fact.serialized_name();
                    menu_item = gtk.MenuItem(' '.join([time, fact_name]))
                    menu_item.connect("activate", self.on_last_activity_activated, fact_name)
                    self.last_activities_menu.append(menu_item)
                    menu_item.show()
        else:
            self.last_activities_item.set_sensitive(False)
    
    def on_last_activity_activated(self, widget, name):
        fact = Fact(name)
        if not fact.activity:
            return
        runtime.storage.add_fact(fact)
        
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
        self.project.load_day()
        facts = self.project.todays_facts
        today_duration = 0
        if facts:
            for fact in facts:
                today_duration += 24 * 60 * fact.delta.days + fact.delta.seconds / 60
#        if self.duration:
#            today_duration += self.duration
        today_duration = "%s:%02d" % (today_duration/60, today_duration%60)
        if self.project.last_activity and end_time is None:
            self._set_activity_status(1)
            delta = dt.datetime.now() - start_time
            duration = delta.seconds /  60
            label = "%s %s" % (last_activity_name,
                               stuff.format_duration(duration, False))
            self.set_activity_text(last_activity_name,
                                 stuff.format_duration(duration, False))
            indicator_label = "%s %s / %sh" % (self._clamp_text(self.activity,
                                         length=self._label_length,
                                         with_ellipsis=False),
                                         self.duration,
                                         today_duration)
        else:
            self._set_activity_status(0)
            label = "%s" % _(u"New activity")
            self.set_activity_text(label, None)
            indicator_label = self._get_no_activity_label(today_duration)

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

    def show(self):
        self.indicator.set_menu(self.menu)
        self.refresh_tray()

    def refresh_tray(self):
        """refresh hamster every x secs - load today, check last activity etc."""
        self.update_label()
        self.update_last_activities()
        return True

    """signals"""
    def after_activity_update(self, widget):
#        self.new_name.refresh_activities()
        self.project.load_day()
        self.update_label()
        self.update_last_activities()

    def after_fact_update(self, event):
        self.project.load_day()
        self.update_label()
        self.update_last_activities()
        
    def on_toggle_called(self, client):
#        self.__show_toggle(not self.button.get_active())
        pass
