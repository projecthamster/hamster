import os, time
from os.path import *
import gnomeapplet, gtk
import hamster, hamster.db
from hamster.About import show_about


class HamsterApplet(object):
    def __init__(self, applet):
        self.applet = applet
        self.label = gtk.Label("Hamster")

        self.last_activity = hamster.db.get_last_activity()

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
        for activity in activities:
            item = gtk.RadioMenuItem(prev_item, activity['name'])

            #set selected
            if self.last_activity and activity['name'] == self.last_activity['name']:
                item.set_active(True);

            item.connect("activate", self.changeActivity, activity['id'])
            menu.add(item)
            prev_item = item
            items.append({'id':activity['id'], 'name':activity['name']})

        separator = gtk.SeparatorMenuItem()
        menu.add(separator)

        menu_edit_activities = gtk.MenuItem('Edit activities');
        menu_edit_activities.connect("activate", edit_activities)
        menu.add(menu_edit_activities)

        menu_show_overview = gtk.MenuItem('Overview');
        menu_show_overview.connect("activate", show_overview)
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
        self.last_activity = hamster.db.add_fact(activity_id)

def edit_activities(menu_item):
    from hamster.activities import ActivitiesEditor
    activities_editor = ActivitiesEditor()
    store = activities_editor.get_store()

    # inform widgets of changes in model
    store.connect("row_changed", activities_changed_cb, menu_item.parent)
    store.connect("rows_reordered", activities_reordered_cb, menu_item.parent)
    store.connect("row_deleted", activity_deleted_cb, menu_item.parent)
    activities_editor.show()

def show_overview(menu_item):
    from hamster.overview import OverviewController
    overview = OverviewController()
    overview.show()


def activities_changed_cb(model, path, row, menu):
    update_menu(menu)

def activities_reordered_cb(model, path, row1, row2, menu):
    update_menu(menu)

def activity_deleted_cb(model, path, menu):
    update_menu(menu)




