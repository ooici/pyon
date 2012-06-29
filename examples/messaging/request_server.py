"""
Run the request_client example once this is running.
"""
from pyon.net import messaging
from pyon.net import channel
from pyon.net.channel import ChannelError, ChannelClosedError, BaseChannel, PublisherChannel, ListenChannel, SubscriberChannel, ServerChannel, BidirClientChannel, ChannelShutdownMessage
from pyon.net.transport import NameTrio

def receive(ch, msg):
    ch.setup_listener(NameTrio('my_exchange', 'my_private_queue'))
    print 'after listen'
    ch.start_consume()
    print 'after consume'
    while msg !='Close12334':
        msg, headers, delivery_tag = ch.recv()
        ch.ack(delivery_tag)
        print 'Message recv: ', msg
    ch.close()

def echo(msg):
    print 'Echo msg:', msg

def listen():
    node, ioloop_process = messaging.make_node()
    ch = node.channel(channel.BidirChannel)
    ch.attach(echo)
    ch.setup_listener(NameTrio('my_exchange', 'my_public_queue5'))
    print 'after listen'
    ch.start_consume()
    print 'after consume'
    msg, headers, delivery_tag = ch.recv()
    print 'Message recv: ', msg
    ch.ack(delivery_tag)
    msg, headers, delivery_tag = ch.recv()
    print 'Message recv: ', msg
    ch.ack(delivery_tag)
    msg, headers, delivery_tag = ch.recv()
    print 'Message recv: ', msg
    ch.ack(delivery_tag)
    """
    with  ch.accept() as newch:
        print 'After accept'
        msg, headers, delivery_tag = newch.recv()
        newch.ack(delivery_tag)
        print 'Message recv: ', msg
        receive(newch, msg)"""
    ch.close()

if __name__ == '__main__':
    receive()
