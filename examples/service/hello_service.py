#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from pyon.util.log import log

from interface.services.examples.hello.ihello_service import BaseHelloService

class HelloService(BaseHelloService):

    def hello(self, text=''):
        log.debug("In hello_service.hello. Text=%s" % text)
        return "BACK:%s" % text

    def noop(self, text=''):
        return "k"



def start(container, starttype, app_definition, config):
    log.debug("Hello app started")
    return (None, None)

def stop(container, state):
    log.debug("Hello app stopped")
