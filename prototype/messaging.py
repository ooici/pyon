from kombu import BrokerConnection
from kombu.messaging import Producer, Consumer, Exchange, Queue

#from gevent import monkey; monkey.patch_all()
import gevent

loremIpsum = '''
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna
aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
'''

msgCount = 0
def receive(body, msg):
    global msgCount
    msgCount += 1
    if msgCount % 50 == 0:
        print 'Recieved message #%d of length %d' % (msgCount, len(body))


def main():
    cfg = {'hostname':'localhost', 'userid':'guest', 'password':'guest', 'virtual_host':'/', 'port':5672}
    transport = 'pika'
    #transport = 'librabbitmq'
    connection = BrokerConnection(transport=transport, **cfg)
    connection.connect()

    cfg = {'name':'simple-test-1', 'auto_delete':True, 'durable':False, 'delivery_mode':'transient'}
    channel = connection.channel()
    exchange = Exchange(channel=channel, **cfg)
    #exchange = exchange_def(channel)

    routing_key = 'simple-test-1-route'
    queue = Queue(exchange=exchange, routing_key=routing_key, **cfg)

    channel = connection.channel()
    producer = Producer(channel=channel, exchange=exchange, routing_key=routing_key)

    channel = connection.channel()
    consumer = Consumer(channel=channel, queues=[queue], callbacks=[receive])
    consumer.consume()

    def serve_forever():
        while True:
            #print 'drain'
            #gevent.sleep(0.0001)
            connection.drain_events(timeout=1)
    def publish_forever():
        while True:
            producer.publish(loremIpsum)
            gevent.sleep(0.0001)

    #g1, g2 = gevent.spawn(publish_forever), gevent.spawn(serve_forever)
    g2 = gevent.spawn(serve_forever)
    g1 = gevent.spawn(publish_forever)
    gevent.joinall([g1, g2])
    #gevent.joinall([gevent.spawn(publish_forever), gevent.spawn(serve_forever)])

if __name__ == '__main__':
    gevent.spawn(main).join()
