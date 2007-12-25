class Storage(object):
    def __init__(self, parent):
        self.parent = parent
        self.run_fixtures()

    def run_fixtures(self):
        pass

    def dispatch(self, event, data):
        self.parent.dispatch(event, data)

    def add_fact(self, activity_name, fact_time = None):
        result = self.__add_fact(activity_name, fact_time)
        if result:
            self.dispatch('fact_updated', result['start_time'])
        return result

    def touch_fact(self, fact, end_time = None):
        end_time = end_time or datetime.datetime.now()
        return self.__touch_fact(fact, end_time)

    def get_facts(self, date):
        return self.__get_facts(date)

    def remove_fact(self, fact_id):
        return self.__remove_fact(fact_id)

    def get_activity_list(self, pattern = "%"):
        return self.__get_activity_list(pattern)

    def remove_activity(self, id):
        return self.__remove_activity(id)

    def swap_activities(self, id1, id2):
        return self.__swap_activities(id1, id2)

    def update_activity(self, activity):
        return self.__update_activity(activity)

