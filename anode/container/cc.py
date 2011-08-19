#!/usr/bin/env python
"""
TODO:
[ ] server and client name argument is a short cut
[ ] generic server and client delivery loop
[ ] decide on how Channel Type is passed/associated with gen server/client
[ ] Entity might be better as a 'factory' that can make handler instances
per request. This will also facilitate the Entity holding 'business'
objects/resources that each request has access to. This will keep the
actual handlers functional. 
"""
__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from anode.base import CFG, messaging, channel, GreenProcessSupervisor

class Container(object):
    """
    The Capability Container. Its purpose is to spawn/monitor processes and services
    that do the bulk of the work in the ION system.
    """
    node = None
    def __init__(self, *args, **kwargs):
        self.proc_sup = GreenProcessSupervisor()

    def start(self):
        self.proc_sup.start() 
        self.node, self.ioloop = messaging.makeNode() # shortcut hack
        self.proc_sup.spawn('green', self.ioloop.join)


    def stop(self):
        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)

    def start_server(self, name, entity):
        """
        Start a new request/response server using the given entity as the
        handler/service
        """
        def generic_server(ch, entity):
            ch.bind(('amq.direct', name))
            ch.listen()
            while True:
                req_chan = ch.accept()
                msg = req_chan.recv()
                entity.message_received(req_chan, msg)

        ch = self.node.channel(channel.Bidirectional)
        self.proc_sup.spawn('green', generic_server, ch, entity)

    def start_client(self, name, entity):
        ch = self.node.channel(channel.BidirectionalClient)
        ch.connect(('amq.direct', name))
        entity.attach_channel(ch)
        def client_recv(ch, entity):
            while True:
                data = ch.recv()
                entity.message_received(data)
        self.proc_sup.spawn('green', client_recv, ch, entity)


    def serve_forever(self):
        if not self.proc_sup.running:
            self.start()
        self.proc_sup.join_children()

