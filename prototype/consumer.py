
import gevent

from zope.interface import Interface, implements

from pyon.service import service
from pyon.net import endpoint
from pyon.container import cc

import time


class MessageCountSampler(object):

    def __init__(self, *args):
        self.entities = args
        self.total_count = 0
        self.last_time = time.time()

    def sample(self):
        _total = 0
        for e in self.entities:
            _total += e.get_count()
        _diff = _total - self.total_count
        self.total_count = _total
        _now_time = time.time()
        d_time = _now_time - self.last_time
        inst_rate = _diff / d_time
        self.last_time = _now_time
        print "count: %s msgs - rate: %s msg/sec " % (str(self.total_count), str(inst_rate),)


class Counter(endpoint.Endpoint):

    def __init__(self):
        self.count = 0

    def get_count(self):
        return self.count

    def message_received(self, msg):
        self.count += 1

def looping_call(interval, callable):
    def loop(interval, callable):
        while True:
            gevent.sleep(interval)
            callable()
    return gevent.spawn(loop, interval, callable)

def main():
    container = cc.Container()
    container.start()

    counter = Counter()
    sampler = MessageCountSampler(counter)
    container.start_subscriber('p_test', counter)

    looping_call(1, sampler.sample)

    container.serve_forever()


if __name__ == '__main__':
    main()
