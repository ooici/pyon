"""
Run the request_server example first.
"""
from pyon.net import messaging
from pyon.net import channel
from pyon.net.transport import NameTrio


def send(text):
    node, ioloop_process = messaging.make_node()
    ch = node.channel(channel.BidirChannel)
    ch.connect(NameTrio('buyer', 'buyer_queue10'))
    msg = text
    ch.send(msg)
    print 'Message send:' + msg
    #print 'Message received: ', data

def start(text):
    node, ioloop_process = messaging.make_node()
    ch = node.channel(channel.BidirChannel)
    ch.connect(NameTrio('my_exchange', 'my_public_queue8'))
    msg = texts
    ch.send(msg)
    print 'Message send:' + msg
    #print 'Message received: ', data

if __name__ == '__main__':
    start('Test')