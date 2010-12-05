import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from hamster.lib import stuff

class TestActivityInputParsing(unittest.TestCase):
    def test_plain_name(self):
        # plain activity name
        activity = stuff.Fact("just a simple case")
        self.assertEquals(activity.activity, "just a simple case")

        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None
        assert activity.description is None

    def test_with_start_time(self):
        # with time
        activity = stuff.Fact("12:35 with start time")
        self.assertEquals(activity.activity, "with start time")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:35")

        #rest must be empty
        assert activity.category is None
        assert activity.end_time is None
        assert activity.description is None

    def test_with_start_and_end_time(self):
        # with time
        activity = stuff.Fact("12:35-14:25 with start-end time")
        self.assertEquals(activity.activity, "with start-end time")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:35")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "14:25")

        #rest must be empty
        assert activity.category is None
        assert activity.description is None

    def test_category(self):
        # plain activity name
        activity = stuff.Fact("just a simple case@hamster")
        self.assertEquals(activity.activity, "just a simple case")
        self.assertEquals(activity.category, "hamster")
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.description is None

    def test_description(self):
        # plain activity name
        activity = stuff.Fact("case, with added description")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.description, "with added description")
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None

    def test_tags(self):
        # plain activity name
        activity = stuff.Fact("case, with added #de description #and, #some #tags")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.description, "with added #de description")
        self.assertEquals(set(activity.tags), set(["and", "some", "tags"]))
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None

    def test_full(self):
        # plain activity name
        activity = stuff.Fact("1225-1325 case@cat, description #ta non-tag #tag #bag")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:25")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "13:25")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.category, "cat")
        self.assertEquals(activity.description, "description #ta non-tag")
        self.assertEquals(set(activity.tags), set(["bag", "tag"]))

if __name__ == '__main__':
    unittest.main()
