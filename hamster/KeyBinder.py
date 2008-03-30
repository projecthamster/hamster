import gtk, gobject, gconf
import hamster, hamster.keybinder
from hamster.Configuration import Configuration

class Keybinder(gobject.GObject):
   __gsignals__ = {
      "activated" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_ULONG]),
      # When the keybinding changes, passes a boolean indicating wether the keybinding is successful
      "changed" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_BOOLEAN]),
   }

   def __init__(self):
      gobject.GObject.__init__(self)
      
      self.bound = False
      self.prevbinding = None
      
      # Set and retreive global keybinding from gconf
      self.configuration = Configuration()
      self.enable_hotkeys = self.configuration.get_enable_hotkeys()
      self.key_combination = self.configuration.get_show_window_hotkey()
      if self.key_combination == None:
         # This is for uninstalled cases, the real default is in the schema
         self.key_combination = "<Alt>Q"
      self.configuration.add_show_window_hotkey_change_notify(lambda x, y, z, a: self.on_config_key_combination(z.value))
      self.configuration.add_enable_hotkeys_change_notify(lambda x, y, z, a: self.on_config_enable_hotkeys(z.value))
      
      if self.enable_hotkeys:
        self.bind()
      
   def on_config_key_combination(self, value=None):
      if value != None and value.type == gconf.VALUE_STRING:
         self.prevbinding = self.key_combination
         self.key_combination = value.get_string()
         if self.enable_hotkeys:
             self.bind()

   def on_config_enable_hotkeys(self, value=None):
        if value:
          value = value.get_bool()
          
        self.enable_hotkeys = value

        if value:
            self.bind()
        else:
            self.prevbinding = self.key_combination
            self.unbind()          
   
   def on_keyboard_shortcut(self):
      self.emit('activated', hamster.keybinder.tomboy_keybinder_get_current_event_time())
   
   def get_key_combination(self):
      return self.key_combination
   
   def bind(self):
      if self.bound:
         self.unbind()
         
      try:
         print 'Binding shortcut %s to popup hamster' % self.key_combination
         hamster.keybinder.tomboy_keybinder_bind(self.key_combination, self.on_keyboard_shortcut)
         self.bound = True
      except KeyError:
         # if the requested keybinding conflicts with an existing one, a KeyError will be thrown
         self.bound = False
      
      self.emit('changed', self.bound)
               
   def unbind(self):
      try:
         print 'Unnding shortcut %s to popup hamster' % self.prevbinding
         hamster.keybinder.tomboy_keybinder_unbind(self.prevbinding)
         self.bound = False
      except KeyError:
         # if the requested keybinding is not bound, a KeyError will be thrown
         pass

if gtk.pygtk_version < (2,8,0):
   gobject.type_register(Keybinder)

keybinder = Keybinder()

def get_hamster_keybinder():
   return keybinder
