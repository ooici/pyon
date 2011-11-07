
class Invocation(object):
    """
    Container object for parameters of events/messages passed to internal
    capability container processes
    """

    # Event outbound processing path
    PATH_OUT = 'outgoing'

    # Event inbound processing path
    PATH_IN = 'incoming'

    def __init__(self, **kwargs):
        self.args = kwargs
        self.path = kwargs.get('path')
        self.message = kwargs.get('message')
        self.headers = kwargs.get('headers') or {}  # ensure dict

class Interceptor(object):
    """
    Basic interceptor model.
    """
    def configure(self, config):
        pass

    def outgoing(self, invocation):
        pass

    def incoming(self, invocation):
        pass

def process_interceptors(interceptors, invocation):
    for interceptor in interceptors:
        func = getattr(interceptor, invocation.path)
        invocation = func(invocation)
    return invocation

def walk(o, cb):
    """
    Utility method to do recursive walking of a possible iterable (inc dicts) and do inline transformations.
    You supply a callback which receives an object. That object may be an iterable (which will then be walked
    after you return it, as long as it remains an iterable), or it may be another object inside of that.

    If a dict is discovered, your callback will receive the dict as a whole and the contents of values only. Keys are left untouched.

    @TODO move to a general utils area?
    """
    if hasattr(o, '__iter__'):
        newo = cb(o)

        # still an iterable? iterate it.
        if hasattr(newo, '__iter__'):
            if isinstance(newo, dict):
                return dict(((k, walk(v, cb)) for k,v in newo.iteritems()))
            else:
                return [walk(x, cb) for x in newo]
        else:
            return newo
    else:
        return cb(o)
