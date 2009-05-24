import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from hamster import stuff

class TestActivityInputParsing(unittest.TestCase):
    def test_plain_name(self):
        # plain activity name
        activity = stuff.parse_activity_input("just a simple case")
        self.assertEquals(activity.activity_name, "just a simple case")
        assert activity.category_name is None and activity.start_time is None \
               and activity.end_time is None and activity.category_name is None\
               and activity.description is None

    def test_with_start_time(self):
        # with time
        activity = stuff.parse_activity_input("12:35 with start time")
        self.assertEquals(activity.activity_name, "with start time")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:35")

        #rest must be empty        
        assert activity.category_name is None \
               and activity.end_time is None and activity.category_name is None\
               and activity.description is None

    def test_with_start_and_end_time(self):
        # with time
        activity = stuff.parse_activity_input("12:35-14:25 with start-end time")
        self.assertEquals(activity.activity_name, "with start-end time")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:35")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "14:25")

        #rest must be empty        
        assert activity.category_name is None \
               and activity.category_name is None\
               and activity.description is None

    def test_category(self):
        # plain activity name
        activity = stuff.parse_activity_input("just a simple case@hamster")
        self.assertEquals(activity.activity_name, "just a simple case")
        self.assertEquals(activity.category_name, "hamster")
        assert activity.start_time is None \
               and activity.end_time is None \
               and activity.description is None

    def test_description(self):
        # plain activity name
        activity = stuff.parse_activity_input("case, with added description")
        self.assertEquals(activity.activity_name, "case")
        self.assertEquals(activity.description, "with added description")
        assert activity.category_name is None and activity.start_time is None \
               and activity.end_time is None and activity.category_name is None

    def test_full(self):
        # plain activity name
        activity = stuff.parse_activity_input("1225-1325 case@cat, description")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:25")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "13:25")
        self.assertEquals(activity.activity_name, "case")
        self.assertEquals(activity.category_name, "cat")
        self.assertEquals(activity.description, "description")

if __name__ == '__main__':
    unittest.main()
