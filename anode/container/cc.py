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

from anode.base import CFG, SERVICE_CFG, messaging, channel, GreenProcessSupervisor
from anode.net import entity

service_cls_by_name = {}

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

        # Read the config file and start services defined there
        # TODO likely should be done elsewhere
        serviceNames = self.readConfig()

        # Iterate over service name list, starting services
        # TODO likely should be done elsewhere
        for serviceName in serviceNames:
            self.start_service(serviceName)

    def stop(self):
        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)

    def start_service(self, name):
        self.start_server(name, entity.RPCEntityFromService(service_cls_by_name[name]))

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

    def readConfig(self):
        # Loop through configured services and start them
        services = SERVICE_CFG['apps']
        # Return value.  Will contain list of
        # service names from the config file
        serviceNames = []
        for serviceDef in services:
            name = serviceDef["name"]

            # Service is described in processapp tuple
            # Field 1 is the module name
            # Field 2 is the class name
            module = serviceDef["processapp"][1]
            cls = serviceDef["processapp"][2]

            clsInstance = self.forname(module, cls)
            service_cls_by_name[name] = clsInstance

            serviceNames.append(name)
        return serviceNames

    def forname(self, modpath, classname):
        ''' Returns a class of "classname" from module "modname". '''
        firstTime = True
        module = __import__(modpath, fromlist=[classname])
        classobj = getattr(module, classname)
        return classobj()

