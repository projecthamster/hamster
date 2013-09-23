'''Tests examine different functions in Fact class from /src/hamster/lib/__init__.py'''

import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from hamster.lib import Fact

class TestFactClass(unittest.TestCase):
    '''Testing Fact class from library'''
    def test_plain_name(self):
        ''' testing plain activity name'''
        activity = Fact("just a simple case")
        self.assertEquals(activity.activity, "just a simple case")

        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None
        assert activity.description is None

    def test_with_start_time(self):
        '''testing start time syntax'''
        activity = Fact("12:35 with start time")
        self.assertEquals(activity.activity, "with start time")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:35")

        #rest must be empty
        assert activity.category is None
        assert activity.end_time is None
        assert activity.description is None

    def test_with_start_and_end_time(self):
        '''testing start time and end time syntax'''
        activity = Fact("12:35-14:25 with start-end time")
        self.assertEquals(activity.activity, "with start-end time")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:35")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "14:25")

        #rest must be empty
        assert activity.category is None
        assert activity.description is None

    def test_category(self):
        '''testing category syntax'''
        activity = Fact("just a simple case@hamster")
        self.assertEquals(activity.activity, "just a simple case")
        self.assertEquals(activity.category, "hamster")
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.description is None

    def test_description(self):
        '''testing description syntax'''
        activity = Fact("case, with added description")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.description, "with added description")
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None

    def test_tags(self):
        '''testing tag syntax, making sure hashtags in description are not pulled as tags'''
        activity = Fact("case, with added#de description #and, #some #tags")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.description, "with added#de description")
        self.assertEquals(set(activity.tags), set(["and", "some", "tags"]))
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None

    def test_full(self):
        '''testing full syntax'''
        activity = Fact("1225-1325 case@cat, description non-tag#ta #tag #bag")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:25")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "13:25")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.category, "cat")
        self.assertEquals(activity.description, "description non-tag#ta")
        self.assertEquals(set(activity.tags), set(["bag", "tag"]))
        
    def test_explicit(self):
        '''testing whether explicit assignments work as defined'''
        activity = Fact(start_time = "12:25", end_time = "13:25", activity = "case", category = "cat", description = "description non-tag#ta", tags = "tag, bag")
        self.assertEquals(activity.start_time, "12:25")
        self.assertEquals(activity.end_time, "13:25")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.category, "cat")
        self.assertEquals(activity.description, "description non-tag#ta")
        self.assertEquals(set(activity.tags), set(["bag", "tag"]))
        
    def test_explicitvsparse(self):
        '''testing whether explicit has precedence over standard syntax'''
        activity = Fact("1225-1325 case@cat, description non-tag#ta #tag #bag", description = "true")
        self.assertEquals(activity.start_time.strftime("%H:%M"), "12:25")
        self.assertEquals(activity.end_time.strftime("%H:%M"), "13:25")
        self.assertEquals(activity.activity, "case")
        self.assertEquals(activity.category, "cat")
        self.assertEquals(activity.description, "true")
        self.assertEquals(set(activity.tags), set(["bag", "tag"]))
    
    def test_easteregg(self):
        '''testing the easter egg (ponies vs rainbows?)'''
        activity = Fact("bbq omg")
        self.assertEquals(activity.activity, "bbq omg")
        self.assertEquals(activity.ponies, True)
        self.assertEquals(activity.description, "[ponies = 1], [rainbows = 0]")

        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None

    def test_iter_explicit(self):
        '''testing iter with explicit assingments'''
        activity = Fact(start_time = "12:34", end_time = "15:12", activity = "test activity", category = "test category", description = "test description", tags = "testtags")
        activity2 = Fact(start_time = "12:34", end_time = "15:12", activity = "test activity", category = "test category", description = "test description", tags = "testtags")
        self.assertEquals([elem for elem in activity], [elem for elem in activity2])
        activity3 = Fact(start_time = "12:14", end_time = "15:12", activity = "test activity", category = "test category", description = "test description", tags = "testtags")
        self.assertNotEqual([elem for elem in activity], [elem for elem in activity3])
        
    def test_serialized_name(self):
        '''testing serialized_name'''
        activity = Fact("case@cat")
        test1 = activity.serialized_name()
        test2 = "case@cat"
        self.assertEquals(test1, test2)
        activity = Fact("case@cat, description #tag #bag")
        test3 = activity.serialized_name()
        test4 = "case@cat,description #tag #bag"
        self.assertEquals(test3, test4)
        
    def test_str(self):
        '''testing str'''
        #first, testing start_time only
        activity = Fact("12:35 with start time")
        t1 = "%s %s" % (activity.start_time.strftime(activity.STRINGFORMAT), activity.serialized_name())
        t2 = str(activity)
        self.assertEquals(t1, t2)
        #now, testing both start_time and end_time
        activity = Fact("12:35-14:25 with start-end time")
        t1 = "%s - %s %s" % (activity.start_time.strftime(activity.STRINGFORMAT), activity.end_time.strftime(activity.TIMESTRINGFORMAT), activity.serialized_name())
        t2 = str(activity)

if __name__ == '__main__':
    unittest.main()
