import os, time
import datetime as dt
from os.path import *
import gnomeapplet, gtk
import gtk.glade
import gobject


import hamster, hamster.db
from hamster.About import show_about
from hamster.overview import DayStore
from hamster.overview import format_duration

class HamsterEventBox(gtk.EventBox):
    __gsignals__ = {
        "toggled"         : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_LONG]),
        "activity_update" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_LONG]),
        "fact_update"     : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_STRING]),
    }
    
    
    def __init__(self):
        gtk.EventBox.__init__(self)
        self.active = False
        self.set_visible_window(False)
        self.connect('button-press-event', self.on_button_press)
    
    def on_button_press(self, widget, event):
        if event.button == 1:
            self.set_active(not self.active)
            return True
                
    def fact_updated(self):
        print "yay!"

    def get_active(self):
        return self.active
    
    def set_active(self, active):
        changed = (self.active != active)
        self.active = active
        
        if changed:
            self.emit("toggled", active)

    def activity_updated(self, renames):
        self.emit("activity_update", renames)

    def fact_updated(self, date):
        self.emit("fact_update", date)


class HamsterApplet(object):
    visible = False # global visibility toggler

    def __init__(self, applet):
        self.applet = applet
        self.label = gtk.Label("Hamster")

        # load window of activity switcher and todays view
        self.w_tree = gtk.glade.XML(os.path.join(hamster.SHARED_DATA_DIR, "menu.glade"))
        self.w_tree.signal_autoconnect(self)
        self.window = self.w_tree.get_widget('menu_window')

        # init today's tree
        self.treeview = self.w_tree.get_widget('today')
        timeColumn = gtk.TreeViewColumn('Time')
        timeColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        timeColumn.set_expand(False)
        timeCell = gtk.CellRendererText()
        timeColumn.pack_start(timeCell, True)
        timeColumn.set_attributes(timeCell, text=2)
        self.treeview.append_column(timeColumn)

        nameColumn = gtk.TreeViewColumn('Name')
        nameColumn.set_expand(True)
        nameCell = gtk.CellRendererText()
        nameColumn.pack_start(nameCell, True)
        nameColumn.set_attributes(nameCell, text=1)
        self.treeview.append_column(nameColumn)
        
        durationColumn = gtk.TreeViewColumn(' ')
        durationColumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        durationColumn.set_expand(False)
        durationCell = gtk.CellRendererText()
        durationColumn.pack_start(durationCell, True)
        durationColumn.set_attributes(durationCell, text=3)
        self.treeview.append_column(durationColumn)
        
        self.today = None
        self.update_status()

        # add a timer so we can update duration of current task
        # a little naggy, still maybe that will remind user to change tasks
        # we go for refresh each minute
        gobject.timeout_add(60000, self.update_status)
        

        # build the menu
        self.refresh_menu()

    
        self.evBox = HamsterEventBox()
        self.evBox.add(self.label)

        self.applet.add(self.evBox)

        self.evBox.connect ("toggled", self.__show_toggle)
        self.evBox.connect ("activity_update", self.after_activity_update)
        self.evBox.connect ("fact_update", self.after_fact_update)

        self.applet.setup_menu_from_file (
            hamster.SHARED_DATA_DIR, "Hamster_Applet.xml",
            None, [
            ("About", self.on_about),
            ])

        self.applet.show_all()
        
    def panel_clicked(self):
        self.evBox.set_active(self, not self.evBox.get_active())
    
    def update_status(self):
        today = time.strftime('%Y%m%d')
        if today != self.today:
            self.load_today()

        if self.last_activity:
            now = time.strftime('%H%M')
            duration = hamster.db.mins(now) - hamster.db.mins(self.last_activity['fact_time'])
            label = "%s: %s" % (self.last_activity['name'], format_duration(duration))
        else:
            label = "Hamster: New day!"

        self.label.set_text(label)
        return True
        
        
    def load_today(self):
        """sets up today's tree and fills it with records
           returns information about last activity"""

        treeview = self.w_tree.get_widget('today')        
        self.today = time.strftime('%Y%m%d')
        day = DayStore(self.today);
        treeview.set_model(day.fact_store)

        if day.facts:
            self.last_activity = day.facts[len(day.facts)-1]
        else:
            self.last_activity = None

    def refresh_menu(self):
        activity_list = self.w_tree.get_widget('activity_list')

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
            
        activity_list.show_all()

        return True
        
    def on_about (self, component, verb):
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
        today = time.strftime('%Y%m%d')
        self.evBox.fact_updated(today)
        self.evBox.set_active(False)

    def edit_activities(self, menu_item):
        self.set_active_main(False)
        
        from hamster.activities import ActivitiesEditor
        activities_editor = ActivitiesEditor(self.evBox)

        activities_editor.show()

    def after_activity_update(self, widget, renames):
        print "activities updated"
        self.refresh_menu()
        if renames:
            print "something renamed"
            self.load_today()
            self.update_status()
    
    def after_fact_update(self, widget, date):
        print "fact updated"
        today = time.strftime('%Y%m%d')

        if date == today:
            print "Fact of today updated"
            self.load_today()
            self.refresh_menu()
            self.update_status()
    
    def show_overview(self, menu_item):
        self.set_active_main(False)
        from hamster.overview import OverviewController
        overview = OverviewController(self.evBox)
        overview.show()

    def show_custom_fact_form(self, menu_item):
        self.set_active_main(False)
        from hamster.add_custom_fact import CustomFactController
        custom_fact = CustomFactController(self.evBox)
        custom_fact.show()

    def after_fact_changes(self, some_object):
        self.load_today()
    

    def __show_toggle(self, widget, is_active):          
        print is_active;
        if is_active:
            self.window.show_all()
        else:
            self.window.hide()

            
    def get_active_main (self):
        return self.evBox.get_active ()
    
    def set_active_main (self, is_active):
        self.evBox.set_active (is_active)
             

