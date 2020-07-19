import dbus

from dbus.mainloop.glib import DBusGMainLoop as DBusMainLoop
from json import dumps, loads
from calendar import timegm
from hamster.lib import datetime as dt
from hamster.lib.fact import Fact


"""D-Bus communication utilities."""

# file layout: functions sorted in alphabetical order,
# not taking into account the "to_" and "from_" prefixes.
# So back and forth conversions are close to one another.


# dates

def from_dbus_date(dbus_date):
    """Convert D-Bus timestamp (seconds since epoch) to date."""
    return dt.date.fromtimestamp(dbus_date) if dbus_date else None


def to_dbus_date(date):
    """Convert date to D-Bus timestamp (seconds since epoch)."""
    return timegm(date.timetuple()) if date else 0


# facts

def from_dbus_fact_json(dbus_fact):
    """Convert D-Bus JSON to Fact."""
    d = loads(dbus_fact)
    range_d = d['range']
    # should use pdt.datetime.fromisoformat,
    # but that appears only in python3.7, nevermind
    start_s = range_d['start']
    end_s = range_d['end']
    range = dt.Range(start=dt.datetime.parse(start_s) if start_s else None,
                     end=dt.datetime.parse(end_s) if end_s else None)
    d['range'] = range
    return Fact(**d)


def to_dbus_fact_json(fact):
    """Convert Fact to D-Bus JSON (str)."""
    d = {}
    keys = ('activity', 'category', 'description', 'tags', 'id', 'activity_id', 'exported')
    for key in keys:
        d[key] = getattr(fact, key)
    # isoformat(timespec="minutes") appears only in python3.6, nevermind
    # and fromisoformat is not available anyway, so let's talk hamster
    start = str(fact.range.start) if fact.range.start else None
    end = str(fact.range.end) if fact.range.end else None
    d['range'] = {'start': start, 'end': end}
    return dumps(d)


# Range

def from_dbus_range(dbus_range):
    """Convert from D-Bus string to dt.Range."""
    range, __ = dt.Range.parse(dbus_range, position="exact")
    return range


def to_dbus_range(range):
    """Convert dt.Range to D-Bus string."""

    # no default_day, to always output in the same format
    return range.format(default_day=None)


# Legacy functions:

"""
old dbus_fact signature (types matching the to_dbus_fact output)
    i  id
    i  start_time
    i  end_time
    s  description
    s  activity name
    i  activity id
    s  category name
    as List of fact tags
    i  date
    i  delta
    b  exported
"""
fact_signature = '(iiissisasiib)'


def from_dbus_fact(dbus_fact):
    """Unpack the struct into a proper dict.

    Legacy: to besuperceded by from_dbus_fact_json at some point.
    """
    return Fact(activity=dbus_fact[4],
                start_time=dt.datetime.utcfromtimestamp(dbus_fact[1]),
                end_time=dt.datetime.utcfromtimestamp(dbus_fact[2]) if dbus_fact[2] else None,
                description=dbus_fact[3],
                activity_id=dbus_fact[5],
                category=dbus_fact[6],
                tags=dbus_fact[7],
                exported=dbus_fact[10],
                id=dbus_fact[0]
                )


def to_dbus_fact(fact):
    """Perform Fact conversion to D-Bus.

    Return the corresponding dbus structure, with supported data types.
    Legacy: to besuperceded by to_dbus_fact_json at some point.
    """
    return (fact.id or 0,
            timegm(fact.start_time.timetuple()),
            timegm(fact.end_time.timetuple()) if fact.end_time else 0,
            fact.description or '',
            fact.activity or '',
            fact.activity_id or 0,
            fact.category or '',
            dbus.Array(fact.tags, signature = 's'),
            to_dbus_date(fact.date),
            fact.delta.days * 24 * 60 * 60 + fact.delta.seconds,
            fact.exported)
