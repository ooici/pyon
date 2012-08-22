#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from pyon.util.log import log

from interface.services.examples.hello.ihello_service import BaseHelloService

class HelloService(BaseHelloService):

    def __init__(self, *args, **kwargs):
        BaseHelloService.__init__(self,*args,**kwargs)


    def on_init(self, *args, **kwargs):
        log.debug("Hello service init. Self.id=%s" % self.id)
        self.container.governance_controller.register_process_operation_precondition(self, 'noop', self.deny_noop )

    def on_start(self, *args, **kwargs):
        log.debug("Hello service start")

    def on_quit(self, *args, **kwargs):
        log.debug("Hello service quit")
        self.container.governance_controller.unregister_process_operation_precondition(self, 'noop', self.deny_noop )

    def hello(self, text=''):
        log.debug("In hello_service.hello. Text=%s" % text)
        return "BACK:%s" % text

    def noop(self, text=''):
        return "k"

    def deny_noop(self, msg, header):
        if header['op'] == 'noop':
            return False, 'The noop operation has been denied'



def start(container, starttype, app_definition, config):
    log.debug("Hello app started")
    return (None, None)

def stop(container, state):
    log.debug("Hello app stopped")
