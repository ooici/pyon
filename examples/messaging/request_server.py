"""
Run the request_client example once this is running.
"""
from pyon.net import messaging
from pyon.net import channel

if __name__ == '__main__':
    node, ioloop_process = messaging.make_node()
    ch = node.channel(channel.Bidirectional)
    ch.bind(('amq.direct', 'server_x'))
    ch.listen()
    connected_ch = ch.accept()
    data = connected_ch.recv()
    print 'Message recvd: ', data
    connected_ch.send('hola')


