#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from pyon.public import log, RT, PRED, LCS

from interface.services.examples.hello.ihello_resource_service import BaseHelloResourceService

class HelloResourceService(BaseHelloResourceService):

    # The following are illustrative and not necessary. Delete if not needed.
    def on_init(self):
        log.debug("Hello resource service init. Self.id=%s" % self.id)

    def on_start(self):
        log.debug("Hello resource service start")

    def on_stop(self):
        log.debug("Hello resource service stop")

    def on_quit(self):
        log.debug("Hello resource service quit")

    def create_my_resource(self, my_resource={}):
        log.debug("create_my_resource(my_resource=%s)" % (my_resource))
        assert my_resource, "Arguments not set"
        import random
        my_resource.num = random.randint(100)
        myres_id,_ = self.clients.resource_registry.create(my_resource)
        return myres_id

    def update_my_resource(self, my_resource={}):
        log.debug("update_my_resource(my_resource=%s)" % (my_resource))
        assert my_resource, "Arguments not set"
        success = self.clients.resource_registry.update(my_resource)
        return success

    def read_my_resource(self, my_resource_id=''):
        log.debug("read_my_resource(my_resource_id=%s)" % (my_resource_id))
        my_resource = self.clients.resource_registry.read(my_resource_id)
        return my_resource

    def delete_my_resource(self, my_resource_id=''):
        self.clients.resource_registry.execute_lifecycle_transition(my_resource_id, LCS.RETIRED)
        return True

    def find_my_resources(self, filters={}):
        res_objs, _ = self.clients.resource_registry.find_resources(RT.SampleResource, None, None, False)
        log.debug("find_my_resources(): Found %s, ids=%s" % (len(res_objs), [o._id for o in res_objs]))
        return res_objs

    def activate_my_resource(self, my_resource_id=''):
        self.clients.resource_registry.execute_lifecycle_transition(my_resource_id, LCS.ACTIVE)
        return True

    def deactivate_my_resource(self, my_resource_id=''):
        self.clients.resource_registry.execute_lifecycle_transition(my_resource_id, LCS.REGISTERED)
        return True
