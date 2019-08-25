import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "../src")))

import unittest
from hamster.lib import Fact
from hamster.lib.stuff import hamster_now


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
        activity = Fact.parse("just a simple case with ütf-8")
        self.assertEqual(activity.activity, "just a simple case with ütf-8")

        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None
        assert activity.description is None

    def test_with_start_time(self):
        # with time
        activity = Fact.parse("12:35 with start time")
        self.assertEqual(activity.activity, "with start time")
        self.assertEqual(activity.start_time.strftime("%H:%M"), "12:35")

        #rest must be empty
        assert activity.category is None
        assert activity.end_time is None
        assert activity.description is None

    def test_with_start_and_end_time(self):
        # with time
        activity = Fact.parse("12:35-14:25 with start-end time")
        self.assertEqual(activity.activity, "with start-end time")
        self.assertEqual(activity.start_time.strftime("%H:%M"), "12:35")
        self.assertEqual(activity.end_time.strftime("%H:%M"), "14:25")

        #rest must be empty
        assert activity.category is None
        assert activity.description is None

    def test_category(self):
        # plain activity name
        activity = Fact.parse("just a simple case@hämster")
        self.assertEqual(activity.activity, "just a simple case")
        self.assertEqual(activity.category, "hämster")
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.description is None

    def test_description(self):
        # plain activity name
        activity = Fact.parse("case, with added descriptiön")
        self.assertEqual(activity.activity, "case")
        self.assertEqual(activity.description, "with added descriptiön")
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None
        assert activity.category is None

    def test_tags(self):
        # plain activity name
        activity = Fact.parse("case, with added #de description #and, #some #tägs")
        self.assertEqual(activity.activity, "case")
        self.assertEqual(activity.description, "with added #de description")
        self.assertEqual(set(activity.tags), set(["and", "some", "tägs"]))
        assert activity.category is None
        assert activity.start_time is None
        assert activity.end_time is None

    def test_full(self):
        # plain activity name
        activity = Fact.parse("1225-1325 case@cat, description #ta non-tag #tag #bäg")
        self.assertEqual(activity.start_time.strftime("%H:%M"), "12:25")
        self.assertEqual(activity.end_time.strftime("%H:%M"), "13:25")
        self.assertEqual(activity.activity, "case")
        self.assertEqual(activity.category, "cat")
        self.assertEqual(activity.description, "description #ta non-tag")
        self.assertEqual(set(activity.tags), set(["bäg", "tag"]))

    def test_copy(self):
        fact1 = Fact.parse("12:25-13:25 case@cat, description #tag #bäg")
        fact2 = fact1.copy()
        self.assertEqual(fact1.start_time, fact2.start_time)
        self.assertEqual(fact1.end_time, fact2.end_time)
        self.assertEqual(fact1.activity, fact2.activity)
        self.assertEqual(fact1.category, fact2.category)
        self.assertEqual(fact1.description, fact2.description)
        self.assertEqual(fact1.tags, fact2.tags)
        fact3 = fact1.copy(activity="changed")
        self.assertEqual(fact3.activity, "changed")
        fact3 = fact1.copy(category="changed")
        self.assertEqual(fact3.category, "changed")
        fact3 = fact1.copy(description="changed")
        self.assertEqual(fact3.description, "changed")
        fact3 = fact1.copy(tags=["changed"])
        self.assertEqual(fact3.tags, ["changed"])

    def test_comparison(self):
        fact1 = Fact.parse("12:25-13:25 case@cat, description #tag #bäg")
        fact2 = fact1.copy()
        self.assertEqual(fact1, fact2)
        fact2 = fact1.copy()
        fact2.activity = "abcd"
        self.assertNotEqual(fact1, fact2)
        fact2 = fact1.copy()
        fact2.category = "abcd"
        self.assertNotEqual(fact1, fact2)
        fact2 = fact1.copy()
        fact2.description = "abcd"
        self.assertNotEqual(fact1, fact2)
        import datetime as dt
        fact2 = fact1.copy()
        fact2.start_time = hamster_now()
        self.assertNotEqual(fact1, fact2)
        fact2 = fact1.copy()
        fact2.end_time = hamster_now()
        self.assertNotEqual(fact1, fact2)
        # wrong order
        fact2 = fact1.copy()
        fact2.tags = ["bäg", "tag"]
        self.assertNotEqual(fact1, fact2)
        # correct order
        fact2 = fact1.copy()
        fact2.tags = ["tag", "bäg"]
        self.assertEqual(fact1, fact2)

    def test_decimal_in_activity(self):
        # cf. issue #270
        fact = Fact.parse("12:25-13:25 10.0@ABC, Two Words #tag #bäg")
        self.assertEqual(fact.activity, "10.0")
        self.assertEqual(fact.category, "ABC")
        self.assertEqual(fact.description, "Two Words")
        # should not pick up a time here
        fact = Fact.parse("10.00@ABC, Two Words #tag #bäg")
        self.assertEqual(fact.activity, "10.00")
        self.assertEqual(fact.category, "ABC")
        self.assertEqual(fact.description, "Two Words")

    def test_spaces(self):
        # cf. issue #114
        fact = Fact.parse("11:00 12:00 BPC-261 - Task title@Project#code")
        self.assertEqual(fact.activity, "BPC-261 - Task title")
        self.assertEqual(fact.category, "Project")
        self.assertEqual(fact.description, None)
        self.assertEqual(fact.tags, ["code"])
        # space between category and tag
        fact2 = Fact.parse("11:00 12:00 BPC-261 - Task title@Project #code")
        self.assertEqual(fact.serialized(), fact2.serialized())

if __name__ == '__main__':
    unittest.main()
