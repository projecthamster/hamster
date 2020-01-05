import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "../src")))

import datetime as dt
import unittest
import re
import hamster.lib.datetime as hdt
from hamster.lib.fact import Fact
from hamster.lib.stuff import (
    datetime_to_hamsterday,
    hamsterday_time_to_datetime,
    hamster_now,
    hamster_today,
    )
from hamster.lib.parsing import (
    dt_pattern,
    _extract_datetime,
    parse_time,
    parse_datetime_range,
    specific_dt_pattern,
    )


class TestActivityInputParsing(unittest.TestCase):
    def test_datetime_to_hamsterday(self):
        date_time = dt.datetime(2018, 8, 13, 23, 10)  # 2018-08-13 23:10
        expected = dt.date(2018, 8, 13)
        self.assertEqual(datetime_to_hamsterday(date_time), expected)
        date_time = dt.datetime(2018, 8, 14, 0, 10)  # 2018-08-14 0:10
        expected = dt.date(2018, 8, 13)
        self.assertEqual(datetime_to_hamsterday(date_time), expected)

    def test_hamsterday_time_to_datetime(self):
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
        assert activity.start_time is None
        assert activity.end_time is None
        assert not activity.category
        assert not activity.description

    def test_with_start_time(self):
        # with time
        activity = Fact.parse("12:35 with start time")
        self.assertEqual(activity.activity, "with start time")
        self.assertEqual(activity.start_time.strftime("%H:%M"), "12:35")

        #rest must be empty
        assert not activity.category
        assert activity.end_time is None
        assert not activity.description

    def test_with_start_and_end_time(self):
        # with time
        activity = Fact.parse("12:35-14:25 with start-end time")
        self.assertEqual(activity.activity, "with start-end time")
        self.assertEqual(activity.start_time.strftime("%H:%M"), "12:35")
        self.assertEqual(activity.end_time.strftime("%H:%M"), "14:25")

        #rest must be empty
        assert not activity.category
        assert not activity.description

    def test_category(self):
        # plain activity name
        activity = Fact.parse("just a simple case@hämster")
        self.assertEqual(activity.activity, "just a simple case")
        self.assertEqual(activity.category, "hämster")
        assert activity.start_time is None
        assert activity.end_time is None
        assert not activity.description

    def test_description(self):
        # plain activity name
        activity = Fact.parse("case,, with added descriptiön")
        self.assertEqual(activity.activity, "case")
        self.assertEqual(activity.description, "with added descriptiön")
        assert not activity.category
        assert activity.start_time is None
        assert activity.end_time is None
        assert not activity.category

    def test_tags(self):
        # plain activity name
        activity = Fact.parse("#case,, description with #hash,, #and, #some #tägs")
        self.assertEqual(activity.activity, "#case")
        self.assertEqual(activity.description, "description with #hash")
        self.assertEqual(set(activity.tags), set(["and", "some", "tägs"]))
        assert not activity.category
        assert activity.start_time is None
        assert activity.end_time is None

    def test_full(self):
        # plain activity name
        activity = Fact.parse("1225-1325 case@cat,, description #ta non-tag,, #tag #bäg")
        self.assertEqual(activity.start_time.strftime("%H:%M"), "12:25")
        self.assertEqual(activity.end_time.strftime("%H:%M"), "13:25")
        self.assertEqual(activity.activity, "case")
        self.assertEqual(activity.category, "cat")
        self.assertEqual(activity.description, "description #ta non-tag")
        self.assertEqual(set(activity.tags), set(["bäg", "tag"]))

    def test_copy(self):
        fact1 = Fact.parse("12:25-13:25 case@cat,, description #tag #bäg")
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
        fact1 = Fact.parse("12:25-13:25 case@cat,, description #tag #bäg")
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
        fact = Fact.parse("12:25-13:25 10.0@ABC,, Two Words #tag #bäg")
        self.assertEqual(fact.activity, "10.0")
        self.assertEqual(fact.category, "ABC")
        self.assertEqual(fact.description, "Two Words")
        # should not pick up a time here
        fact = Fact.parse("10.00@ABC,, Two Words #tag #bäg")
        self.assertEqual(fact.activity, "10.00")
        self.assertEqual(fact.category, "ABC")
        self.assertEqual(fact.description, "Two Words")

    def test_spaces(self):
        # cf. issue #114
        fact = Fact.parse("11:00 12:00 BPC-261 - Task title@Project#code")
        self.assertEqual(fact.activity, "BPC-261 - Task title")
        self.assertEqual(fact.category, "Project")
        self.assertEqual(fact.description, "")
        self.assertEqual(fact.tags, ["code"])
        # space between category and tag
        fact2 = Fact.parse("11:00 12:00 BPC-261 - Task title@Project #code")
        self.assertEqual(fact.serialized(), fact2.serialized())
        # empty fact
        fact3 = Fact()
        self.assertEqual(fact3.serialized(), "")

    def test_commas(self):
        fact = Fact.parse("11:00 12:00 activity, with comma@category,, description, with comma")
        self.assertEqual(fact.activity, "activity, with comma")
        self.assertEqual(fact.category, "category")
        self.assertEqual(fact.description, "description, with comma")
        self.assertEqual(fact.tags, [])
        fact = Fact.parse("11:00 12:00 activity, with comma@category,, description, with comma, #tag1, #tag2")
        self.assertEqual(fact.activity, "activity, with comma")
        self.assertEqual(fact.category, "category")
        self.assertEqual(fact.description, "description, with comma")
        self.assertEqual(fact.tags, ["tag1", "tag2"])
        fact = Fact.parse("11:00 12:00 activity, with comma@category,, description, with comma and #hash,, #tag1, #tag2")
        self.assertEqual(fact.activity, "activity, with comma")
        self.assertEqual(fact.category, "category")
        self.assertEqual(fact.description, "description, with comma and #hash")
        self.assertEqual(fact.tags, ["tag1", "tag2"])

    def test_roundtrips(self):
        for start_time in (
            None,
            dt.time(12, 33),
            ):
            for end_time in (
                None,
                dt.time(13,34),
                ):
                for activity in (
                    "activity",
                    "#123 with two #hash",
                    "activity, with comma",
                    ):
                    for category in (
                        "",
                        "category",
                        ):
                        for description in (
                            "",
                            "description",
                            "with #hash",
                            "with, comma",
                            "with @at",
                            ):
                            for tags in (
                                [],
                                ["single"],
                                ["with space"],
                                ["two", "tags"],
                                ["with @at"],
                                ):
                                start = hamsterday_time_to_datetime(hamster_today(),
                                                                    start_time
                                                                    ) if start_time else None
                                end = hamsterday_time_to_datetime(hamster_today(),
                                                                  end_time
                                                                  ) if end_time else None
                                if end and not start:
                                    # end without start is not parseable
                                    continue
                                fact = Fact(start_time=start,
                                            end_time=end,
                                            activity=activity,
                                            category=category,
                                            description=description,
                                            tags=tags)
                                for range_pos in ("head", "tail"):
                                    fact_str = fact.serialized(range_pos=range_pos)
                                    parsed = Fact.parse(fact_str, range_pos=range_pos)
                                    self.assertEqual(fact, parsed)
                                    self.assertEqual(parsed.activity, fact.activity)
                                    self.assertEqual(parsed.category, fact.category)
                                    self.assertEqual(parsed.description, fact.description)
                                    self.assertEqual(parsed.tags, fact.tags)


class TestDatetime(unittest.TestCase):
    def test_rounding(self):
        dt1 = hdt.datetime(2019, 12, 31, hour=13, minute=14, second=10, microsecond=11)
        self.assertEqual(dt1.second, 0)
        self.assertEqual(dt1.microsecond, 0)
        self.assertEqual(str(dt1), "2019-12-31 13:14")


class TestParsers(unittest.TestCase):
    def test_parse_time(self):
        self.assertEqual(parse_time("9:01"), dt.time(9, 1))
        self.assertEqual(parse_time("9.01"), dt.time(9, 1))
        self.assertEqual(parse_time("12:01"), dt.time(12, 1))
        self.assertEqual(parse_time("12.01"), dt.time(12, 1))
        self.assertEqual(parse_time("1201"), dt.time(12, 1))

    def test_dt_patterns(self):
        p = specific_dt_pattern(1)
        s = "12:03"
        m = re.fullmatch(p, s, re.VERBOSE)
        time = _extract_datetime(m, d="date1", h="hour1", m="minute1", r="relative1",
                                default_day=hamster_today())
        self.assertEqual(time.strftime("%H:%M"), "12:03")
        s = "2019-12-01 12:36"
        m = re.fullmatch(p, s, re.VERBOSE)
        time = _extract_datetime(m, d="date1", h="hour1", m="minute1", r="relative1")
        self.assertEqual(time.strftime("%Y-%m-%d %H:%M"), "2019-12-01 12:36")
        s = "-25"
        m = re.fullmatch(p, s, re.VERBOSE)
        timedelta = _extract_datetime(m, d="date1", h="hour1", m="minute1", r="relative1",
                                     default_day=hamster_today())
        self.assertEqual(timedelta, dt.timedelta(minutes=-25))
        s = "2019-12-05"
        m = re.search(p, s, re.VERBOSE)
        self.assertEqual(m, None)


    def test_parse_datetime_range(self):
        # only match clean
        s = "10.00@cat"
        start, end, rest = parse_datetime_range(s, position="head")
        self.assertEqual(start, None)
        self.assertEqual(end, None)
        s = "12:02"
        start, end, rest = parse_datetime_range(s)
        self.assertEqual(start.strftime("%H:%M"), "12:02")
        self.assertEqual(end, None)
        s = "12:03 13:04"
        start, end, rest = parse_datetime_range(s)
        self.assertEqual(start.strftime("%H:%M"), "12:03")
        self.assertEqual(end.strftime("%H:%M"), "13:04")
        s = "12:35 activity"
        start, end, rest = parse_datetime_range(s, position="head")
        self.assertEqual(start.strftime("%H:%M"), "12:35")
        self.assertEqual(end, None)
        s = "2019-12-01 12:33 activity"
        start, end, rest = parse_datetime_range(s, position="head")
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-12-01 12:33")
        self.assertEqual(end, None)

        ref = dt.datetime(2019, 11, 29, 13, 55)  # 2019-11-29 13:55

        s = "-25 activity"
        start, end, rest = parse_datetime_range(s, position="head", ref=ref)
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-11-29 13:30")
        self.assertEqual(end, None)
        s = "-55 -25 activity"
        start, end, rest = parse_datetime_range(s, position="head", ref=ref)
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-11-29 13:00")
        self.assertEqual(end.strftime("%Y-%m-%d %H:%M"), "2019-11-29 13:30")
        s = "-55 -120 activity"
        start, end, rest = parse_datetime_range(s, position="head", ref=ref)
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-11-29 13:00")
        self.assertEqual(end.strftime("%Y-%m-%d %H:%M"), "2019-11-29 11:55")

        s = "2019-12-05"  # single hamster day
        start, end, rest = parse_datetime_range(s, ref=ref)
        just_before = start - dt.timedelta(seconds=1)
        just_after = end + dt.timedelta(seconds=1)
        self.assertEqual(datetime_to_hamsterday(just_before), dt.date(2019, 12, 4))
        self.assertEqual(datetime_to_hamsterday(just_after), dt.date(2019, 12, 6))
        s = "2019-12-05 2019-12-07"  # hamster days range
        start, end, rest = parse_datetime_range(s, ref=ref)
        just_before = start - dt.timedelta(seconds=1)
        just_after = end + dt.timedelta(seconds=1)
        self.assertEqual(datetime_to_hamsterday(just_before), dt.date(2019, 12, 4))
        self.assertEqual(datetime_to_hamsterday(just_after), dt.date(2019, 12, 8))


if __name__ == '__main__':
    unittest.main()
