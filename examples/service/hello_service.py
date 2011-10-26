#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from pyon.util.log import log

from interface.services.ihello_service import BaseHelloService

class HelloService(BaseHelloService):

    def hello(self, text=''):
        log.debug("In hello_service.hello. Text=%s" % text)
        return "BACK:%s" % text
