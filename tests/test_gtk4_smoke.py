"""Smoke tests verifying GTK4 widgets instantiate without exceptions."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('PangoCairo', '1.0')

from gi.repository import Gtk as gtk


class TestGtk4WidgetInstantiation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def test_scene_creates(self):
        from hamster.lib.graphics import Scene
        scene = Scene()
        self.assertIsNotNone(scene)

    def test_scene_event_creates(self):
        from hamster.lib.graphics import SceneEvent
        event = SceneEvent(x=10, y=20, keyval=65, state=0)
        copy = event.copy()
        self.assertEqual(copy.x, 10)
        self.assertEqual(copy.keyval, 65)

    def test_builder_loads_ui_files(self):
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        for ui_file in ['date_range.ui', 'edit_activity.ui', 'preferences.ui']:
            path = os.path.join(data_dir, ui_file)
            if os.path.exists(path):
                builder = gtk.Builder()
                builder.add_from_file(path)
                self.assertIsNotNone(builder)

    def test_stats_ui_deleted(self):
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.assertFalse(os.path.exists(os.path.join(data_dir, 'stats.ui')))


if __name__ == '__main__':
    unittest.main()
