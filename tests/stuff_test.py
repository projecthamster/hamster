import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "../src")))

import datetime as pdt
import unittest
import re
from hamster.lib import datetime as dt
from hamster.lib.dbus import (
    to_dbus_fact,
    to_dbus_fact_json,
    to_dbus_range,
    from_dbus_fact,
    from_dbus_fact_json,
    from_dbus_range,
    )
from hamster.lib.fact import Fact


class TestFact(unittest.TestCase):

    def test_range(self):
        t1 = dt.datetime(2020, 1, 15, 13, 30)
        t2 = dt.datetime(2020, 1, 15, 15, 30)
        range = dt.Range(t1, t2)
        fact = Fact(range=range)
        self.assertEqual(fact.range.start, t1)
        self.assertEqual(fact.range.end, t2)
        fact = Fact(start=t1, end=t2)
        self.assertEqual(fact.range.start, t1)
        self.assertEqual(fact.range.end, t2)
        # backward compatibility (before v3.0)
        fact = Fact(start_time=t1, end_time=t2)
        self.assertEqual(fact.range.start, t1)
        self.assertEqual(fact.range.end, t2)


class TestFactParsing(unittest.TestCase):

    def test_plain_name(self):
        # plain activity name
        activity = Fact.parse("just a simple case with ütf-8")
        self.assertEqual(activity.activity, "just a simple case with ütf-8")
        assert activity.start_time is None
        assert activity.end_time is None
        assert not activity.category
        assert not activity.description

    def test_only_range(self):
        fact = Fact.parse("-20")
        assert not fact.activity
        fact = Fact.parse("-20 -10")
        assert not fact.activity

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
        fact2 = fact1.copy()
        fact2.range.start = fact1.range.start + dt.timedelta(minutes=1)
        self.assertNotEqual(fact1, fact2)
        fact2 = fact1.copy()
        fact2.range.end = fact1.range.end + dt.timedelta(minutes=1)
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

    # ugly. Really need pytest
    def test_roundtrips(self):
        for start_time in (
            None,
            dt.time(12, 33),
            ):
            for end_time in (
                None,
                dt.time(13, 34),
                ):
                for activity in (
                    "activity",
                    "#123 with two #hash",
                    "activity, with comma",
                    "17.00 tea",
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
                            "multiline\ndescription",
                            ):
                            for tags in (
                                [],
                                ["single"],
                                ["with space"],
                                ["two", "tags"],
                                ["with @at"],
                                ):
                                start = dt.datetime.from_day_time(dt.hday.today(),
                                                                  start_time
                                                                  ) if start_time else None
                                end = dt.datetime.from_day_time(dt.hday.today(),
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
                                    self.assertEqual(parsed.range.start, fact.range.start)
                                    self.assertEqual(parsed.range.end, fact.range.end)
                                    self.assertEqual(parsed.activity, fact.activity)
                                    self.assertEqual(parsed.category, fact.category)
                                    self.assertEqual(parsed.description, fact.description)
                                    self.assertEqual(parsed.tags, fact.tags)


class TestDatetime(unittest.TestCase):
    def test_datetime_from_day_time(self):
        day = dt.date(2018, 8, 13)
        time = dt.time(23, 10)
        expected = dt.datetime(2018, 8, 13, 23, 10)  # 2018-08-13 23:10
        self.assertEqual(dt.datetime.from_day_time(day, time), expected)
        day = dt.date(2018, 8, 13)
        time = dt.time(0, 10)
        expected = dt.datetime(2018, 8, 14, 0, 10)  # 2018-08-14 00:10
        self.assertEqual(dt.datetime.from_day_time(day, time), expected)

    def test_format_timedelta(self):
        delta = dt.timedelta(minutes=10)
        self.assertEqual(delta.format("human"), "10min")
        delta = dt.timedelta(hours=5, minutes=0)
        self.assertEqual(delta.format("human"), "5h")
        delta = dt.timedelta(hours=5, minutes=10)
        self.assertEqual(delta.format("human"), "5h 10min")
        delta = dt.timedelta(hours=5, minutes=10)
        self.assertEqual(delta.format("HH:MM"), "05:10")

    def test_datetime_hday(self):
        date_time = dt.datetime(2018, 8, 13, 23, 10)  # 2018-08-13 23:10
        expected = dt.date(2018, 8, 13)
        self.assertEqual(date_time.hday(), expected)
        date_time = dt.datetime(2018, 8, 14, 0, 10)  # 2018-08-14 0:10
        expected = dt.date(2018, 8, 13)
        self.assertEqual(date_time.hday(), expected)
        today = dt.hday.today()
        self.assertEqual(type(today), dt.hday)

    def test_parse_date(self):
        date = dt.date.parse("2020-01-05")
        self.assertEqual(date, pdt.date(2020, 1, 5))

    def test_parse_time(self):
        self.assertEqual(dt.time.parse("9:01"), pdt.time(9, 1))
        self.assertEqual(dt.time.parse("9.01"), pdt.time(9, 1))
        self.assertEqual(dt.time.parse("12:01"), pdt.time(12, 1))
        self.assertEqual(dt.time.parse("12.01"), pdt.time(12, 1))
        self.assertEqual(dt.time.parse("1201"), pdt.time(12, 1))

    def test_parse_datetime(self):
        self.assertEqual(dt.datetime.parse("2020-01-05 9:01"), pdt.datetime(2020, 1, 5, 9, 1))

    def test_datetime_patterns(self):
        p = dt.datetime.pattern(1)
        s = "12:03"
        m = re.fullmatch(p, s, re.VERBOSE)
        time = dt.datetime._extract_datetime(m, d="date1", h="hour1", m="minute1", r="relative1",
                                              default_day=dt.hday.today())
        self.assertEqual(time.strftime("%H:%M"), "12:03")
        s = "2019-12-01 12:36"
        m = re.fullmatch(p, s, re.VERBOSE)
        time = dt.datetime._extract_datetime(m, d="date1", h="hour1", m="minute1", r="relative1")
        self.assertEqual(time.strftime("%Y-%m-%d %H:%M"), "2019-12-01 12:36")
        s = "-25"
        m = re.fullmatch(p, s, re.VERBOSE)
        relative = dt.datetime._extract_datetime(m, d="date1", h="hour1", m="minute1", r="relative1",
                                                  default_day=dt.hday.today())
        self.assertEqual(relative, dt.timedelta(minutes=-25))
        s = "2019-12-05"
        m = re.search(p, s, re.VERBOSE)
        self.assertEqual(m, None)

    def test_parse_datetime_range(self):
        # only match clean
        s = "10.00@cat"
        (start, end), rest = dt.Range.parse(s, position="head")
        self.assertEqual(start, None)
        self.assertEqual(end, None)
        s = "12:02"
        (start, end), rest = dt.Range.parse(s)
        self.assertEqual(start.strftime("%H:%M"), "12:02")
        self.assertEqual(end, None)
        s = "12:03 13:04"
        (start, end), rest = dt.Range.parse(s)
        self.assertEqual(start.strftime("%H:%M"), "12:03")
        self.assertEqual(end.strftime("%H:%M"), "13:04")
        s = "12:35 activity"
        (start, end), rest = dt.Range.parse(s, position="head")
        self.assertEqual(start.strftime("%H:%M"), "12:35")
        self.assertEqual(end, None)
        s = "2019-12-01 12:33 activity"
        (start, end), rest = dt.Range.parse(s, position="head")
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-12-01 12:33")
        self.assertEqual(end, None)

        ref = dt.datetime(2019, 11, 29, 13, 55)  # 2019-11-29 13:55

        s = "-25 activity"
        (start, end), rest = dt.Range.parse(s, position="head", ref=ref)
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-11-29 13:30")
        self.assertEqual(end, None)
        s = "+25 activity"
        (start, end), rest = dt.Range.parse(s, position="head", ref=ref)
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-11-29 14:20")
        self.assertEqual(end, None)
        s = "-55 -25 activity"
        (start, end), rest = dt.Range.parse(s, position="head", ref=ref)
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-11-29 13:00")
        self.assertEqual(end.strftime("%Y-%m-%d %H:%M"), "2019-11-29 13:30")
        s = "+25 +55 activity"
        (start, end), rest = dt.Range.parse(s, position="head", ref=ref)
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-11-29 14:20")
        self.assertEqual(end.strftime("%Y-%m-%d %H:%M"), "2019-11-29 14:50")
        s = "-55 -120 activity"
        (start, end), rest = dt.Range.parse(s, position="head", ref=ref)
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-11-29 13:00")
        self.assertEqual(end.strftime("%Y-%m-%d %H:%M"), "2019-11-29 11:55")
        s = "-50 20 activity"
        (start, end), rest = dt.Range.parse(s, position="head", ref=ref)
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2019-11-29 13:05")
        self.assertEqual(end.strftime("%Y-%m-%d %H:%M"), "2019-11-29 13:25")

        s = "2019-12-05"  # single hamster day
        (start, end), rest = dt.Range.parse(s, ref=ref)
        just_before = start - dt.timedelta(seconds=1)
        just_after = end + dt.timedelta(seconds=1)
        self.assertEqual(just_before.hday(), pdt.date(2019, 12, 4))
        self.assertEqual(just_after.hday(), pdt.date(2019, 12, 6))
        s = "2019-12-05 2019-12-07"  # hamster days range
        (start, end), rest = dt.Range.parse(s, ref=ref)
        just_before = start - dt.timedelta(seconds=1)
        just_after = end + dt.timedelta(seconds=1)
        self.assertEqual(just_before.hday(), dt.date(2019, 12, 4))
        self.assertEqual(just_after.hday(), dt.date(2019, 12, 8))

        s = "14:30 - --"
        (start, end), rest = dt.Range.parse(s, ref=ref)
        self.assertEqual(start.strftime("%H:%M"), "14:30")
        self.assertEqual(end, None)

    def test_range(self):
        day = dt.hday(2020, 2, 2)
        time = dt.time(21, 20)
        base = dt.datetime.from_day_time(day, time)
        range = dt.Range(base, base + dt.timedelta(minutes=30))
        range_str = range.format(default_day=day)
        self.assertEqual(range_str, "21:20 - 21:50")
        range = dt.Range(None, base)
        range_str = range.format(default_day=day)
        self.assertEqual(range_str, "-- - 21:20")
        # issue #576
        start = dt.datetime(2020, 3, 8, 17, 7)
        end = dt.datetime(2020, 3, 8, 18, 6)
        range = dt.Range.from_start_end(start, end)
        self.assertEqual(range.start, start)
        self.assertEqual(range.end, end)
        # check passthrough
        range2 = dt.Range.from_start_end(range)
        self.assertEqual(range2.start, range.start)
        self.assertEqual(range2.end, range.end)

    def test_rounding(self):
        dt1 = dt.datetime(2019, 12, 31, hour=13, minute=14, second=10, microsecond=11)
        self.assertEqual(dt1.second, 0)
        self.assertEqual(dt1.microsecond, 0)
        self.assertEqual(str(dt1), "2019-12-31 13:14")

    def test_type_stability(self):
        dt1 = dt.datetime(2020, 1, 10, hour=13, minute=30)
        dt2 = dt.datetime(2020, 1, 10, hour=13, minute=40)
        delta = dt2 - dt1
        self.assertEqual(type(delta), dt.timedelta)
        _sum = dt1 + delta
        self.assertEqual(_sum, dt.datetime(2020, 1, 10, hour=13, minute=40))
        self.assertEqual(type(_sum), dt.datetime)
        _sub = dt1 - delta
        self.assertEqual(_sub, dt.datetime(2020, 1, 10, hour=13, minute=20))
        self.assertEqual(type(_sub), dt.datetime)

        opposite = - delta
        self.assertEqual(opposite, dt.timedelta(minutes=-10))
        self.assertEqual(type(opposite), dt.timedelta)
        _sum = delta + delta
        self.assertEqual(_sum, dt.timedelta(minutes=20))
        self.assertEqual(type(_sum), dt.timedelta)
        _sub = delta - delta
        self.assertEqual(_sub, dt.timedelta())
        self.assertEqual(type(_sub), dt.timedelta)

    def test_timedelta(self):
        delta = dt.timedelta(seconds=90)
        self.assertEqual(delta.total_minutes(), 1.5)


class TestDBus(unittest.TestCase):
    def test_round_trip(self):
        fact = Fact.parse("11:00 12:00 activity, with comma@category,, description, with comma #and #tags")
        dbus_fact = to_dbus_fact_json(fact)
        return_fact = from_dbus_fact_json(dbus_fact)
        self.assertEqual(return_fact, fact)

        dbus_fact = to_dbus_fact(fact)
        return_fact = from_dbus_fact(dbus_fact)
        self.assertEqual(return_fact, fact)

        fact = Fact.parse("11:00 activity")
        dbus_fact = to_dbus_fact_json(fact)
        return_fact = from_dbus_fact_json(dbus_fact)
        self.assertEqual(return_fact, fact)

        dbus_fact = to_dbus_fact(fact)
        return_fact = from_dbus_fact(dbus_fact)
        self.assertEqual(return_fact, fact)

        range, __ = dt.Range.parse("2020-01-19 11:00 - 2020-01-19 12:00")
        dbus_range = to_dbus_range(range)
        return_range = from_dbus_range(dbus_range)
        self.assertEqual(return_range, range)


if __name__ == '__main__':
    unittest.main()
