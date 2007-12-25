class Dispatcher(object):
    def dispatch(self, event, data):
        print 'Dispatching event %s (%s)' % (event, data)

