import os, time
import datetime as dt
from os.path import *
import gnomeapplet, gtk
import hamster, hamster.db
from hamster.About import show_about


class HamsterApplet(object):
    def __init__(self, applet):
        self.applet = applet
        self.label = gtk.Label("Hamster")

        self.last_activity = hamster.db.get_last_activity()

        today = time.strftime('%Y%m%d')
        if (self.last_activity['fact_date'] == int(today)):
            self.label.set_text(self.last_activity['name'])

        self.menu = gtk.Menu()
        # build the menu
        self.activities = self.update_menu(self.menu)


        self.evBox = gtk.EventBox()
        self.evBox.add(self.label)
        self.evBox.connect("button-press-event", self.clicked)
        self.evBox.connect("enter-notify-event", self.on_tooltip)
        self.applet.add(self.evBox)

        self.tooltip = gtk.Tooltips()
        self.tooltip.set_tip(self.evBox, "Hello, me is hamster!");
        self.tooltip.enable()


        self.applet.setup_menu_from_file (
            hamster.SHARED_DATA_DIR, "Hamster_Applet.xml",
            None, [
            ("About", self.on_about),
            ])

        self.applet.show_all()

    def update_menu(self, menu):
        #remove all items
        children = menu.get_children()
        for child in children:
            menu.remove(child)

        #populate fresh list from DB
        activities = hamster.db.get_activity_list()
        prev_item = None

        items = []
        today = time.strftime('%Y%m%d')
        for activity in activities:
            item = gtk.RadioMenuItem(prev_item, activity['name'])

            #set selected
            if self.last_activity \
               and activity['name'] == self.last_activity['name'] \
               and (self.last_activity['fact_date'] == int(today)):
                item.set_active(True);

            item.connect("activate", self.changeActivity, activity['id'])
            menu.add(item)
            prev_item = item
            items.append({'id':activity['id'], 'name':activity['name']})

        menu_show_custom_fact = gtk.MenuItem('Add custom fact...');
        menu_show_custom_fact.connect("activate", self.show_custom_fact_form)
        menu.add(menu_show_custom_fact)

        separator = gtk.SeparatorMenuItem()
        menu.add(separator)

        menu_edit_activities = gtk.MenuItem('Edit activities');
        menu_edit_activities.connect("activate", self.edit_activities)
        menu.add(menu_edit_activities)

        menu_show_overview = gtk.MenuItem('Overview');
        menu_show_overview.connect("activate", self.show_overview)
        menu.add(menu_show_overview)

        menu.show_all()

        return items

    def clicked(self, event_box, event):
        if event.button == 1:
            self.menu.popup(None, None, None, event.button, gtk.get_current_event_time())

    def on_tooltip(self, event_box, event):
        today = time.strftime('%Y%m%d')
        now = time.strftime('%H%M')

        if self.last_activity:
          if (self.last_activity['fact_date'] != int(today)):
              tooltip = "Nothing done today!"
          else:
              # we are adding 0.1 because we don't have seconds but
              # would like to differ between nothing and just started something
              duration = hamster.db.mins(now) - hamster.db.mins(self.last_activity['fact_time']) + 0.1

              if duration < 1:
                  tooltip = "Just started '%s'!" % (self.last_activity['name'])
              else:
                  if duration < 60:
                      duration = "%d minutes" % (duration)
                  else:
                      duration = "%.1fh hours" % (duration / 60.0)

                  tooltip = "You have been doing '%s' for %s" % (self.last_activity['name'], duration)
        else:
          tooltip = "Welcome to hamster, define your activities!"

        self.tooltip.set_tip(event_box, tooltip)

    def on_about (self, component, verb):
        show_about(self.applet)

    def changeActivity(self, menu, activity_id):
        today = int(time.strftime('%Y%m%d'))
        fact_time = time.strftime('%H%M')

        # let's do some checks to see how we change activity
        if (self.last_activity 
            and self.last_activity['fact_date'] == today):
           
            # avoid dupes
            if self.last_activity['activity_id'] == activity_id:
                return

            # if the time  since previous minute is about minute 
            # then we consider that user has apparently mistaken and delete
            # the previous task
            current_mins = hamster.db.mins(fact_time)
            prev_mins = hamster.db.mins(self.last_activity['fact_time'])
            
            if (1 >= current_mins - prev_mins > 0): 
                hamster.db.remove_fact(self.last_activity['id'])
                fact_time = self.last_activity['fact_time']

        
    
        self.last_activity = hamster.db.add_fact(activity_id, fact_time = fact_time)
        self.label.set_text(hamster.db.get_last_activity()['name'])

    def refresh_last_activity(self):
        self.last_activity = hamster.db.get_last_activity()

    def edit_activities(self, menu_item):
        from hamster.activities import ActivitiesEditor
        activities_editor = ActivitiesEditor()
        store = activities_editor.get_store()

        # inform widgets of changes in model
        store.connect("row_changed", self.activities_changed_cb, menu_item.parent)
        store.connect("rows_reordered", self.activities_reordered_cb, menu_item.parent)
        store.connect("row_deleted", self.activity_deleted_cb, menu_item.parent)
        activities_editor.show()

    def activities_reordered_cb(self, model, path, row1, row2, menu):
        self.update_menu(menu)

    def activities_changed_cb(self, model, path, row, menu):
        self.update_menu(menu)

    def activity_deleted_cb(self, model, path, menu):
        self.update_menu(menu)

    def show_overview(self, menu_item):
        from hamster.overview import OverviewController
        overview = OverviewController()
        overview.show()

    def show_custom_fact_form(self, menu_item):
        from hamster.add_custom_fact import CustomFactController
        custom_fact = CustomFactController()
        custom_fact.window.connect("destroy", self.post_custom_fact)
        custom_fact.show()

    def post_custom_fact(self, some_object):
        self.refresh_last_activity()
    



