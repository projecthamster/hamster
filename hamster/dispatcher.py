class Dispatcher(object):
    def __init__(self):
        self.handlers = {}

    def add_handler(self, event, method):
        if not self.handlers.has_key(event):
            self.handlers[event] = []
        if not method in self.handlers[event]:
            self.handlers[event].append(method)

    def del_handler(self, event, method):
        if self.handlers.has_key(event):
            if method in self.handlers[event]:
                self.handlers[event].remove(method)

    def dispatch(self, event, data):
        print 'Dispatching event %s (%s)' % (event, data)
        if self.handlers.has_key(event):
            for handler in self.handlers[event]:
                print 'using handler %s' % handler
                handler(event, data)
        else:
            print 'Missing handler for event %s' % event
