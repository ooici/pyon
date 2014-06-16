#!/usr/bin/env python

__author__ = 'Adam R. Smith'

from pyon.public import log
from pyon.service import service
from pyon.net import entity
from pyon.container import cc
from pyon.service.service import BaseService
from interface.services.iping_service import IPingService

from zope.interface import implements
import bottle
from bottle import request, response, route

container = None

class PingService(BaseService):
    implements(IPingService)

    def ping(self, pong='pong'):
        print 'in ping'
        return 'pong'

class BridgeService(BaseService):
    #implements(IBridgeService)

    def __init__(self, port=8080, debug=False):
        self.app = bottle.app()
        bottle.debug(debug)
        bottle.run(self.app, host='0.0.0.0', port=port)

    @route('/')
    def index():
        print 'index'
        ping_client = entity.RPCClientEntityFromInterface(IPingService)
        container.start_client('ooibridge', ping_client)
        pong = ping_client.ping()
        return 'Ping said: %s' % pong


if __name__ == '__main__':
    container = cc.Container()
    container.start() # :(
    print 'container started'

    #ping_client = entity.RPCClientEntityFromInterface(IPingService)
    #container.start_client('ooibridge', ping_client)
    #print 'client started'

    bridge_service = BridgeService(port=8080, debug=True)
    bridge_entity = entity.RPCEntityFromService(bridge_service)
    container.start_server('ooibridge', bridge_entity)
    print 'service started'
    
    container.serve_forever()
    