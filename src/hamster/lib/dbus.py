import datetime as dt
import dbus
import dbus.service
from calendar import timegm
from dbus.mainloop.glib import DBusGMainLoop as DBusMainLoop
from hamster.lib import Fact


"""D-Bus communication utilities."""


def from_dbus_fact(dbus_fact):
    """unpack the struct into a proper dict"""
    return Fact(activity=dbus_fact[4],
                start_time=dt.datetime.utcfromtimestamp(dbus_fact[1]),
                end_time=dt.datetime.utcfromtimestamp(dbus_fact[2]) if dbus_fact[2] else None,
                description=dbus_fact[3],
                activity_id=dbus_fact[5],
                category=dbus_fact[6],
                tags=dbus_fact[7],
                id=dbus_fact[0]
                )


def to_dbus_fact(fact):
    """Perform the conversion between fact database query and
    dbus supported data types
    """
    return (fact['id'],
            timegm(fact['start_time'].timetuple()),
            timegm(fact['end_time'].timetuple()) if fact['end_time'] else 0,
            fact['description'] or '',
            fact['name'] or '',
            fact['activity_id'] or 0,
            fact['category'] or '',
            dbus.Array(fact['tags'], signature = 's'),
            timegm(fact['date'].timetuple()),
            fact['delta'].days * 24 * 60 * 60 + fact['delta'].seconds)
