import datetime

class Storage(object):
    def __init__(self, parent):
        self.parent = parent
        self.run_fixtures()

    def run_fixtures(self):
        pass

    def dispatch(self, event, data):
        self.parent.dispatch(event, data)

    def get_fact(self, id):
        return self.__get_fact(id)

    def add_fact(self, activity_name, fact_time = None):
        result = self.__add_fact(activity_name, fact_time)
        if result:
            self.dispatch('day_updated', result['start_time'])
        return result

    def touch_fact(self, fact, end_time = None):
        end_time = end_time or datetime.datetime.now()
        result = self.__touch_fact(fact, end_time)
        self.dispatch('day_updated', fact['start_time'])
        return result

    def get_facts(self, date):
        return self.__get_facts(date)

    def remove_fact(self, fact_id):
        fact = self.get_fact(fact_id)
        result = self.__remove_fact(fact_id)
        self.dispatch('day_updated', fact['start_time'])
        return result

    def get_activity_list(self, inactive = False, pattern = "%"):
        return self.__get_activity_list(inactive = inactive, pattern = pattern)

    def remove_activity(self, id):
        result = self.__remove_activity(id)
        self.dispatch('activity_updated', ())
        return result

    def swap_activities(self, id1, id2):
        return self.__swap_activities(id1, id2)

    def update_activity(self, activity):
        result = self.__update_activity(activity)
        self.dispatch('activity_updated', ())
        return result

