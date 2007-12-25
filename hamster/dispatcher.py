class Dispatcher(object):
    def __init__(self):
        self.handlers = {}

    def set_handler(self, event, method):
        self.handlers[event] = method

    def dispatch(self, event, data):
        print 'Dispatching event %s (%s)' % (event, data)
        if self.handlers.has_key(event):
            self.handlers[event](event, data)
        else:
            print 'Missing handler for event %s' % event
