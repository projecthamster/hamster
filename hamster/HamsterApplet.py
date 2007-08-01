import os, time
from os.path import *
import gnomeapplet, gtk
import hamster, hamster.db
from hamster.About import show_about


class HamsterApplet(object):
    def __init__(self, applet):
        self.applet = applet
        self.label = gtk.Label("Hamster")

        self.menu = gtk.Menu()
        # build the menu
        update_menu(self.menu)


        self.evBox = gtk.EventBox()
        self.evBox.add(self.label)
        self.evBox.connect("button-press-event", self.clicked)
        self.applet.add(self.evBox)

        self.applet.setup_menu_from_file (
            hamster.SHARED_DATA_DIR, "Hamster_Applet.xml",
            None, [
            ("About", self.on_about),
            ])

        self.applet.show_all()

    def clicked(self, event_box, event):
        if event.button == 1:
            self.menu.popup(None, None, None, event.button, gtk.get_current_event_time())

    def on_about (self, component, verb):
        show_about(self.applet)


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

def changeActivity(menu, activity_id):
    hamster.db.add_fact(activity_id)

def update_menu(menu):
    #remove all items
    children = menu.get_children()
    for child in children:
        menu.remove(child)

    #populate fresh list from DB
    activities = hamster.db.get_activity_list()
    for activity in activities:
        item = gtk.MenuItem(activity['name'])
        item.connect("activate", changeActivity, activity['id'])
        menu.add(item)

    separator = gtk.SeparatorMenuItem()
    menu.add(separator)

    menu_edit_activities = gtk.MenuItem('Edit activities');
    menu_edit_activities.connect("activate", edit_activities)
    menu.add(menu_edit_activities)

    menu_show_overview = gtk.MenuItem('Overview');
    menu_show_overview.connect("activate", show_overview)
    menu.add(menu_show_overview)

    menu.show_all()


