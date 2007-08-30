import os, time
import datetime as dt
from os.path import *
import gnomeapplet, gtk
import gtk.glade


import hamster, hamster.db
from hamster.About import show_about
from hamster.overview import DayStore


class HamsterApplet(object):
    def __init__(self, applet):
        self.applet = applet
        self.label = gtk.Label("Hamster")

        self.menu_wTree = gtk.glade.XML(os.path.join(hamster.SHARED_DATA_DIR, "menu.glade"))
        self.menu_wTree.signal_autoconnect(self)
        self.window = self.menu_wTree.get_widget('menu_window')
        self.visible = False



        treeview = self.menu_wTree.get_widget('today')
        timeColumn = gtk.TreeViewColumn('Time')
        timeColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        timeColumn.set_expand(False)
        timeCell = gtk.CellRendererText()
        timeColumn.pack_start(timeCell, True)
        timeColumn.set_attributes(timeCell, text=2)
        treeview.append_column(timeColumn)

        nameColumn = gtk.TreeViewColumn('Name')
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_attributes(nameCell, text=1)
        treeview.append_column(nameColumn)
        
        durationColumn = gtk.TreeViewColumn(' ')
        durationColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        durationColumn.set_expand(False)
        durationCell = gtk.CellRendererText()
        durationColumn.pack_start(durationCell, True)
        durationColumn.set_attributes(durationCell, text=3)
        treeview.append_column(durationColumn)


        self.last_activity = self.load_today()

        if (self.last_activity):
            self.label.set_text(self.last_activity['name'])


        self.activity_list = self.menu_wTree.get_widget('activity_list')
        # build the menu
        self.activities = self.update_menu(self.activity_list)

    
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
        
    def load_today(self):
        """sets up today's tree and fills it with records
           returns information about last activity"""

        treeview = self.menu_wTree.get_widget('today')        
        today = time.strftime('%Y%m%d')
        day = DayStore(today);
        treeview.set_model(day.fact_store)

        if day.facts:
            return day.facts[len(day.facts)-1]
        else:
            return None

    def update_menu(self, activity_list):
        #remove all items
        children = activity_list.get_children()
        for child in children:
            activity_list.remove(child)

        #populate fresh list from DB
        activities = hamster.db.get_activity_list()
        prev_item = None

        items = []
        today = time.strftime('%Y%m%d')
        for activity in activities:
            item = gtk.RadioButton(prev_item, activity['name'])

            #set selected
            if self.last_activity and activity['name'] == self.last_activity['name']:
                item.set_active(True);

            activity_list.add(item)
            item.connect("clicked", self.changeActivity, activity['id'])
            prev_item = item
            items.append({'id':activity['id'], 'name':activity['name']})

        return items
        
    def clicked(self, event_box, event):
        if event.button == 1:
            self.toggle_window()

    def on_tooltip(self, event_box, event):
        today = time.strftime('%Y%m%d')
        now = time.strftime('%H%M')

        if self.last_activity:
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
            tooltip = "Nothing done today!"

        self.tooltip.set_tip(event_box, tooltip)

    def on_about (self, component, verb):
        self.toggle_window()
        show_about(self.applet)

    def changeActivity(self, item, activity_id):
        if item.get_active() == False:
            return
            
        fact_time = time.strftime('%H%M')

        # let's do some checks to see how we change activity
        if (self.last_activity):
           
            # avoid dupes
            if self.last_activity['activity_id'] == activity_id:
                return

            # if the time  since previous minute is about minute 
            # then we consider that user has apparently mistaken and delete
            # the previous task
            current_mins = hamster.db.mins(fact_time)
            prev_mins = hamster.db.mins(self.last_activity['fact_time'])
            
            print current_mins, prev_mins
            print 1 >= current_mins - prev_mins > 0
            
            if (1 >= current_mins - prev_mins >= 0): 
                hamster.db.remove_fact(self.last_activity['id'])
                fact_time = self.last_activity['fact_time']

        
    
        hamster.db.add_fact(activity_id, fact_time = fact_time)
        self.label.set_text(hamster.db.get_last_activity()['name'])
        self.last_activity = self.load_today()
        self.toggle_window()

    def edit_activities(self, menu_item):
        self.toggle_window()
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
        self.window.queue_resize()

    def activity_deleted_cb(self, model, path, menu):
        self.update_menu(menu)

    def show_overview(self, menu_item):
        self.toggle_window()
        from hamster.overview import OverviewController
        overview = OverviewController()

        # TODO - grab some real signals here!
        overview.window.connect("destroy", self.post_fact_changes)
        overview.show()

    def show_custom_fact_form(self, menu_item):
        self.toggle_window()
        from hamster.add_custom_fact import CustomFactController
        custom_fact = CustomFactController()
        custom_fact.window.connect("destroy", self.post_fact_changes)
        custom_fact.show()

    def post_fact_changes(self, some_object):
        self.load_today()
    

    def toggle_window(self):
        if self.visible:
            self.window.hide()
        else:
            self.window.show_all()
        
        self.visible = not self.visible

