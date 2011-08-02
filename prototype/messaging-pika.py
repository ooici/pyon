from gevent import monkey; monkey.patch_all()
import gevent
from gevent.event import Event

import multiprocessing as mp
import time
from functools import wraps
from setproctitle import setproctitle

#from pika.adapters import BlockingConnection as Connection
from pika.adapters import SelectConnection as Connection
from pika import ConnectionParameters, BasicProperties

import pika
#setattr(pika.adapters.select_connection, 'SELECT_TYPE', 'select')

loremIpsum = '''
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna
aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
'''

def spawn(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        return gevent.spawn(f, *args, **kwds)
    return wrapper

def gevent_switch():
    gevent.getcurrent().switch()

def blocking_cb(func, cb_arg, *args, **kwargs):
    """
    Wrap a function that takes a callback as a named parameter, to block and return its arguments as the result.
    Really handy for working with callback-based APIs. Do not use in really frequently-called code.
    If keyword args are supplied, they come through in a single dictionary to avoid out-of-order issues.
    """
    ev = Event()
    ret_vals = []
    def cb(*args, **kwargs):
        ret_vals.extend(args)
        if len(kwargs): ret_vals.append(kwargs)
        ev.set()
    kwargs[cb_arg] = cb
    func(*args, **kwargs)
    ev.wait()
    if len(ret_vals) == 0:
        return None
    elif len(ret_vals) == 1:
        return ret_vals[0]
    return tuple(ret_vals)

class ReceiverTracker(object):
    def __init__(self, proc_id):
        self.proc_id = proc_id
        self.start()

    def start(self):
        self.msg_count = 0
        self.time_start = time.time()

    def receive(self, channel, method, header, body):
        self.msg_count += 1
        if self.msg_count % 500 == 0:
            time_now = time.time()
            time_diff = time_now - self.time_start
            msgs_sec = self.msg_count/time_diff
            print '%d> Received message #%d of length %d. Doing %.2f msgs/sec' % (
                   self.proc_id, self.msg_count, len(body), msgs_sec)

    def msgs_per_sec(self):
        time_now = time.time()
        time_diff = time_now - self.time_start
        msgs_sec = self.msg_count/time_diff
        return msgs_sec

class Receiver(object):
    def __init__(self, proc_id, params, tracker, routing_key, connection=None):
        self.proc_id = proc_id
        self.tracker = tracker
        self.routing_key = routing_key
        
        if connection is not None:
            self.connection = connection
        else:
            self.connection = Connection(params)
        self.consume_channel = blocking_cb(self.connection.channel, 'on_open_callback')
        print self.consume_channel
        #print '%d> Connected and ready to consume' % (self.proc_id)

    @spawn
    def start_receiving(self, msg_limit, finished):
        self.consume_channel.basic_consume(self.tracker.receive, queue=self.routing_key)
        while True:
            if self.tracker.msg_count == msg_limit:
                finished.set()
                break

            self.consume_channel.transport.connection.process_data_events()
            gevent_switch()

class Publisher(object):
    def __init__(self, proc_id, params, routing_key, properties, connection=None):
        self.proc_id = proc_id
        if connection is not None:
            self.connection = connection
        else:
            self.connection = Connection(params)
        self.publish_channel = blocking_cb(self.connection.channel, 'on_open_callback')
        print self.publish_channel
        self.routing_key = routing_key
        self.properties = properties

        #print '%d> Connected and ready to publish' % (self.proc_id)

    def publish(self, body):
        self.publish_channel.basic_publish(exchange='', routing_key=self.routing_key,
                                           body=body, properties=self.properties)

    @spawn
    def start_publishing(self, msg_limit):
        for i in xrange(msg_limit):
            self.publish(loremIpsum)
            gevent_switch()


def message_process(proc_id, msg_limit=20000, msgs_per_sec=None, send_first=True):
    print 'Starting process %d' % (proc_id)
    
    cfg = {'host':'localhost', 'virtual_host':'/', 'port':5672}
    params = ConnectionParameters(**cfg)
    connection = Connection(params)
    gevent.spawn(connection.ioloop.start)

    exchange_name = 'simple-test-1'
    cfg = {'auto_delete':True, 'durable':False, 'exclusive':False}
    channel = blocking_cb(connection.channel, 'on_open_callback')
    print channel
    #exchange = channel.exchange_declare(exchange=exchange_name, **cfg)

    routing_key = 'simple-test-1-route-%d' % proc_id
    queue = blocking_cb(channel.queue_declare, 'callback', queue=routing_key, **cfg)
    print queue

    properties = BasicProperties(content_type='text/plain', delivery_mode=1)

    worker_count = 5
    msgs_per_worker = msg_limit/worker_count
    assert(int(msgs_per_worker) == msgs_per_worker)     # things will break otherwise

    publishers = [Publisher(proc_id, params, routing_key, properties) for i in xrange(worker_count)]
    publishers = [pub.start_publishing(msgs_per_worker) for pub in publishers]
    if send_first:
        gevent.joinall(publishers)

    rtracker = ReceiverTracker(proc_id)
    receivers = [Receiver(proc_id, params, rtracker, routing_key) for i in xrange(worker_count)]
    rtracker.start()
    finished = Event()
    receivers = [rec.start_receiving(msg_limit, finished) for rec in receivers]
    finished.wait()
    gevent.killall(receivers)

    mps = rtracker.msgs_per_sec()
    print '%d> mps: %.2f' % (proc_id, mps)
    if msgs_per_sec: msgs_per_sec.value += mps
    return mps

def main():
    print 'Here'
    setproctitle('messaging-pika')

    total_messages = 10000

    spawn_procs = False
    if spawn_procs:
        process_count = mp.cpu_count()
        msgs_per_proc = total_messages/process_count
        assert(int(msgs_per_proc) == msgs_per_proc)     # things will break otherwise

        msgs_per_sec_sync = mp.Value('f', 0)
        processes = [mp.Process(target=message_process, args=(i, msgs_per_proc, msgs_per_sec_sync))
                     for i in xrange(process_count)]
        [proc.start() for proc in processes]
        [proc.join() for proc in processes]

        msgs_per_sec = msgs_per_sec_sync.value
    else:
        msgs_per_sec = message_process(1, total_messages)

    print 'Total messages per second: %.2f' % (msgs_per_sec)

# This next block monkey-patches pika for a 5-10% performance boost as a proof of concept.
'''
import pika
import pika.spec as spec
def _my_send_method(self, channel_number, method, content=None):
    """
    Constructs a RPC method frame and then sends it to the broker
    """
    self._send_frame(pika.frame.Method(channel_number, method))

    if isinstance(content, tuple):
        props = content[0]
        body = content[1]
    else:
        props = None
        body = content

    if props:
        length = 0
        if body:
            length = len(body)
        self._send_frame(pika.frame.Header(channel_number, length, props))

    if body:
        max_piece = (self.parameters.frame_max - \
                     spec.FRAME_HEADER_SIZE - \
                     spec.FRAME_END_SIZE)

        for i in xrange(0, len(body), max_piece):
            piece = body[i:i + max_piece]
            self._send_frame(pika.frame.Body(channel_number, piece))

setattr(Connection, '_send_method', _my_send_method)
'''

if __name__ == '__main__':
    gevent.spawn(main).join()
    #main()