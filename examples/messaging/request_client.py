"""
Run the request_server example first.
"""
from pyon.net import messaging
from pyon.net import channel

if __name__ == '__main__':
    node, ioloop_process = messaging.make_node()
    ch = node.channel(channel.BidirectionalClient)
    ch.connect(('amq.direct', 'server_x'))
    ch.send('hello')
    data = ch.recv()
    print 'Message recvd: ', data


