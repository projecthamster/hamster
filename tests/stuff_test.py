import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from hamster.lib import Fact

class TestActivityInputParsing(unittest.TestCase):
    def test_plain_name(self):
        # plain activity name
        activity = Fact("just a simple case")
        self.assertEquals(activity.activity, "just a simple case")

        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None
        assert activity.description is None

    def test_with_start_time(self):
        # with time
        activity = Fact("12:35 with start time")
        self.assertEquals(activity.activity, "with start time")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:35")

        #rest must be empty
        assert activity.category is None
        assert activity.end_time is None
        assert activity.description is None

    def test_with_start_and_end_time(self):
        # with time
        activity = Fact("12:35-14:25 with start-end time")
        self.assertEquals(activity.activity, "with start-end time")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:35")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "14:25")

        #rest must be empty
        assert activity.category is None
        assert activity.description is None

    def test_category(self):
        # plain activity name
        activity = Fact("just a simple case@hamster")
        self.assertEquals(activity.activity, "just a simple case")
        self.assertEquals(activity.category, "hamster")
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.description is None

    def test_description(self):
        # plain activity name
        activity = Fact("case, with added description")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.description, "with added description")
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None

    def test_tags(self):
        # plain activity name
        activity = Fact("case, with added#de description #and, #some #tags")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.description, "with added#de description")
        self.assertEquals(set(activity.tags), set(["and", "some", "tags"]))
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None

    def test_full(self):
        # plain activity name
        activity = Fact("1225-1325 case@cat, description non-tag#ta #tag #bag")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:25")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "13:25")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.category, "cat")
        self.assertEquals(activity.description, "description non-tag#ta")
        self.assertEquals(set(activity.tags), set(["bag", "tag"]))
        
    def test_explicit(self):
        # testing whether explicit works
        activity = Fact(start_time = "12:25", end_time = "13:25", activity = "case", category = "cat", description = "description non-tag#ta", tags = "tag, bag")
        self.assertEquals(activity.start_time, "12:25")
        self.assertEquals(activity.end_time, "13:25")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.category, "cat")
        self.assertEquals(activity.description, "description non-tag#ta")
        self.assertEquals(set(activity.tags), set(["bag", "tag"]))
        
    def test_explicitvsparse(self):
        #testing whether explicit has precedence
        activity = Fact("1225-1325 case@cat, description non-tag#ta #tag #bag", description = "true")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:25")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "13:25")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.category, "cat")
        self.assertEquals(activity.description, "true")
        self.assertEquals(set(activity.tags), set(["bag", "tag"]))
    
    def test_easteregg(self):
        #ponies?
        activity = Fact("bbq omg")
        self.assertEquals(activity.activity, "bbq omg")
        self.assertEquals(activity.ponies, True)
        self.assertEquals(activity.description, "[ponies = 1], [rainbows = 0]")

        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None

    def test_iter_explicit(self):
        #testing iter under explicit
        activity = Fact(start_time = "12:34", end_time = "15:12", activity = "test activity", category = "test category", description = "test description", tags = "testtags")
        activity2 = Fact(start_time = "12:34", end_time = "15:12", activity = "test activity", category = "test category", description = "test description", tags = "testtags")
        self.assertEquals([elem for elem in activity], [elem for elem in activity2])
        activity3 = Fact(start_time = "12:14", end_time = "15:12", activity = "test activity", category = "test category", description = "test description", tags = "testtags")
        self.assertNotEqual([elem for elem in activity], [elem for elem in activity3])

if __name__ == '__main__':
    unittest.main()
