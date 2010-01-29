#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

import dbus
import datetime as dt

HAMSTER_DBUS_PATH = "/org/gnome/Hamster"
HAMSTER_DBUS_IFACE = "org.gnome.Hamster"



if __name__ == "__main__":
    bus = dbus.SessionBus()
    obj = bus.get_object(HAMSTER_DBUS_IFACE, HAMSTER_DBUS_PATH)
    hamster = dbus.Interface(obj, "org.gnome.Hamster")


    facts = []
    for fact in hamster.GetFacts(0, 0):
        # run through the facts and convert them to python types so it's easier to operate with
        res = {}
        for key in ['name', 'category', 'description']:
            res[key] = str(fact[key])

        for key in ['start_time', 'end_time', 'date']:
            res[key] = dt.datetime.utcfromtimestamp(fact[key]) if fact[key] else None

        res['delta'] = dt.timedelta(days = fact['delta'] / (60 * 60 * 24),
                                    seconds = fact['delta'] % (60 * 60 * 24))

        res['tags'] = [str(tag) for tag in fact['tags']] if fact['tags'] else []

        facts.append(res)

    print "here are your facts!", facts
