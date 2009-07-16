import dbus
import unittest
import datetime as dt

from string import letters
from random import choice
from calendar import timegm

from hamster.hamsterdbus import HAMSTER_PATH, HAMSTER_URI

def rndstr(length=10):
    result = ''
    for i in range(1,10): 
        result += choice(letters)

    return result

class TestTracking(unittest.TestCase):
    def setUp(self):
        self.bus = dbus.SessionBus()
        self.hamster = self.bus.get_object(HAMSTER_URI, HAMSTER_PATH)

        self.addfact = self.hamster.get_dbus_method('AddFact')
        self.getfactbyid = self.hamster.get_dbus_method('GetFactById')
        self.removefact = self.hamster.get_dbus_method('RemoveFact')
        self.getfacts = self.hamster.get_dbus_method('GetFacts')
        self.getcurrentfact = self.hamster.get_dbus_method('GetCurrentFact')
        self.addactivity = self.hamster.get_dbus_method('AddActivity')
        self.getactivities = self.hamster.get_dbus_method('GetActivities')
        self.removeactivity = self.hamster.get_dbus_method('RemoveActivity')
        self.addcategory = self.hamster.get_dbus_method('AddCategory')
        self.getcategories = self.hamster.get_dbus_method('GetCategories')
        self.removecategory = self.hamster.get_dbus_method('RemoveCategory')
        self.stoptracking = self.hamster.get_dbus_method('StopTracking')

    def test_addfact(self):
        fact = self.__rndfactgenerator()

        activity = fact['name'] + '@' + fact['category'] + ',' + \
                fact['description']
        fact_id = self.addfact(activity, fact['start_time'], fact['end_time'])
        self.failUnless(type(fact_id) == dbus.Int32 and fact_id != 0, 
            'expected non-zero dbus.Int32 as return value')

        dbfact = self.getfactbyid(fact_id)
        self.assertEqual(fact['name'], dbfact['name'], 
                'expected same activity name')
        self.assertEqual(fact['category'], dbfact['category'], 
                'expected same category name')
        self.assertEqual(fact['description'], dbfact['description'], 
                'expected same description name')
        self.assertEqual(fact['start_time'], dbfact['start_time'], 
                'expected same start_time')
        self.assertEqual(fact['end_time'], dbfact['end_time'], 
                'expected same end_time')

        facts = self.getfacts(dbfact['start_time'], dbfact['end_time'])
        in_facts = False
        for item in facts:
            if item == dbfact:
                in_facts = True
        self.assertTrue(in_facts, 'expected fact between %i and %i' % \
                (fact['start_time'], fact['end_time']))

        self.removeactivity(dbfact['name'], dbfact['category'])
        result = self.__findactivity(dbfact['name'], dbfact['category'])
        self.assertFalse(result, 'not expecting %s@%s in database' % \
                (dbfact['name'], dbfact['category']))

        self.removecategory(dbfact['category'])
        result = self.__findcategory(dbfact['category'])
        self.assertFalse(result, 'not expecting %s in database' % \
                dbfact['category'])

        self.removefact(fact_id)
        deletedfact = self.getfactbyid(fact_id)
        self.assertFalse(deletedfact, 'expected no fact after deleted it')

    def test_getcurrent_stop(self):
        fact = self.__rndfactgenerator()

        activity = fact['name'] + '@' + fact['category'] + ',' + \
                fact['description']
        fact_id = self.addfact(activity, fact['start_time'], 0)
        self.failUnless(type(fact_id) == dbus.Int32 and fact_id != 0, 
            'expected non-zero dbus.Int32 as return value')

        current = self.getcurrentfact()
        self.assertEqual(fact['name'], current['name'], 
                'expected same activity name')
        self.assertEqual(fact['category'], current['category'], 
                'expected same category name')
        self.assertEqual(fact['description'], current['description'], 
                'expected same description name')
        self.assertEqual(fact['start_time'], current['start_time'], 
                'expected same start_time')
        self.assertEqual(0, current['end_time'], 
                'expected same end_time')

        self.stoptracking()
        current = self.getcurrentfact()
        self.assertFalse(current, 'expected no fact after stop tracking')

        self.removeactivity(fact['name'], fact['category'])
        result = self.__findactivity(fact['name'], fact['category'])
        self.assertFalse(result, 'not expecting %s@%s in database' % \
                (fact['name'], fact['category']))

        self.removecategory(fact['category'])
        result = self.__findcategory(fact['category'])
        self.assertFalse(result, 'not expecting %s in database' % \
                fact['category'])

    def test_activity(self):
        act = rndstr()
        cat = rndstr()

        self.addactivity(act, cat)
        result = self.__findactivity(act, cat)
        self.assertTrue(result, 'expecting %s@%s has been created' % (act, cat))

        self.removeactivity(act, cat)
        result = self.__findactivity(act, cat)
        self.assertFalse(result, 'not expecting %s@%s in database' % (act, cat))

        self.removecategory(cat)
        result = self.__findcategory(cat)
        self.assertFalse(result, 'not expecting %s in database' % cat)

    def test_category(self):
        cat = rndstr()

        self.addcategory(cat)
        result = self.__findcategory(cat)
        self.assertTrue(result, 'expecting %s has been created' % cat)

        self.removecategory(cat)
        result = self.__findcategory(cat)
        self.assertFalse(result, 'not expecting %s in database' % cat)

    def __rndfactgenerator(self, name=None, category=None, description=None,
            start_time=None, end_time=None):
        fact = {'name':name or rndstr(), 'category':category or rndstr(), 
                'description':description or rndstr(), 
                'start_time':start_time or timegm(dt.datetime.now().timetuple()), 
                'end_time':end_time or timegm((dt.datetime.now() + \
                        dt.timedelta(hours=1)).timetuple())}
        return fact

    def __findactivity(self, act, cat):
        found = False
        for activity, category in self.getactivities():
            if activity.lower() == act.lower() and \
                    category.lower() == cat.lower():
                found = True
        return found

    def __findcategory(self, cat):
        found = False
        for category in self.getcategories():
            if category.lower() == cat.lower():
                found = True
        return found

if __name__ == '__main__':
    unittest.main()
