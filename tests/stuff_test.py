import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "../src")))

import unittest
from hamster.lib import Fact


class TestActivityInputParsing(unittest.TestCase):
    def test_datetime_to_hamsterday(self):
        import datetime as dt
        from hamster.lib import datetime_to_hamsterday
        date_time = dt.datetime(2018, 8, 13, 23, 10)  # 2018-08-13 23:10
        expected = dt.date(2018, 8, 13)
        self.assertEqual(datetime_to_hamsterday(date_time), expected)
        date_time = dt.datetime(2018, 8, 14, 0, 10)  # 2018-08-14 0:10
        expected = dt.date(2018, 8, 13)
        self.assertEqual(datetime_to_hamsterday(date_time), expected)

    def test_hamsterday_time_to_datetime(self):
        import datetime as dt
        from hamster.lib import hamsterday_time_to_datetime
        hamsterday = dt.date(2018, 8, 13)
        time = dt.time(23, 10)
        expected = dt.datetime(2018, 8, 13, 23, 10)  # 2018-08-13 23:10
        self.assertEqual(hamsterday_time_to_datetime(hamsterday, time), expected)
        hamsterday = dt.date(2018, 8, 13)
        time = dt.time(0, 10)
        expected = dt.datetime(2018, 8, 14, 0, 10)  # 2018-08-14 00:10
        self.assertEqual(hamsterday_time_to_datetime(hamsterday, time), expected)

    def test_plain_name(self):
        # plain activity name
        activity = Fact("just a simple case")
        self.assertEqual(activity.activity, "just a simple case")

        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None
        assert activity.description is None

    def test_with_start_time(self):
        # with time
        activity = Fact("12:35 with start time")
        self.assertEqual(activity.activity, "with start time")
        self.assertEqual(activity.start_time.strftime("%H:%M"), "12:35")

        #rest must be empty
        assert activity.category is None
        assert activity.end_time is None
        assert activity.description is None

    def test_with_start_and_end_time(self):
        # with time
        activity = Fact("12:35-14:25 with start-end time")
        self.assertEqual(activity.activity, "with start-end time")
        self.assertEqual(activity.start_time.strftime("%H:%M"), "12:35")
        self.assertEqual(activity.end_time.strftime("%H:%M"), "14:25")

        #rest must be empty
        assert activity.category is None
        assert activity.description is None

    def test_category(self):
        # plain activity name
        activity = Fact("just a simple case@hamster")
        self.assertEqual(activity.activity, "just a simple case")
        self.assertEqual(activity.category, "hamster")
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.description is None

    def test_description(self):
        # plain activity name
        activity = Fact("case, with added description")
        self.assertEqual(activity.activity, "case")
        self.assertEqual(activity.description, "with added description")
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None

    def test_tags(self):
        # plain activity name
        activity = Fact("case, with added #de description #and, #some #tags")
        self.assertEqual(activity.activity, "case")
        self.assertEqual(activity.description, "with added #de description")
        self.assertEqual(set(activity.tags), set(["and", "some", "tags"]))
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None

    def test_full(self):
        # plain activity name
        #  FIXME: the original string did not require the colon for time:
        # activity = Fact("1225-1325 case@cat, description #ta non-tag #tag #bag")
        activity = Fact("12:25-13:25 case@cat, description #ta non-tag #tag #bag")
        self.assertEqual(activity.start_time.strftime("%H:%M"), "12:25")
        self.assertEqual(activity.end_time.strftime("%H:%M"), "13:25")
        self.assertEqual(activity.activity, "case")
        self.assertEqual(activity.category, "cat")
        self.assertEqual(activity.description, "description #ta non-tag")
        self.assertEqual(set(activity.tags), set(["bag", "tag"]))

if __name__ == '__main__':
    unittest.main()
