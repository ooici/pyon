#!/usr/bin/env python

"""Conversation Log"""

__author__ = 'Prashant Kediyal'
__license__ = 'Apache 2.0'


from pyon.core import bootstrap
from pyon.core.exception import BadRequest
from pyon.datastore.datastore import DataStore
from pyon.net.endpoint import Subscriber
from pyon.util.async import spawn
from pyon.util.log import log

from interface.objects import ConversationMessage

# @TODO: configurable
CONV_DS_NAME = 'conversations'


class ConvSubscriber(Subscriber):

    def __init__(self,  callback=None, pattern='#', *args, **kwargs):
        """
        Note: a ConversationSubscriber needs to be closed to free broker resources
        """
        self._cbthread = None
        self.binding = pattern

        log.debug("ConversationSubscriber pattern %s", self.binding)

        Subscriber.__init__(self, binding=self.binding, callback=callback, **kwargs)

    def start(self):
        """
        Pass in a subscriber here, this will make it listen in a background greenlet.
        """
        assert not self._cbthread, "start called twice on ConversationSubscriber"
        gl = spawn(self.listen)
        self._cbthread = gl
        self._ready_event.wait(timeout=5)
        log.info("ConversationSubscriber started; pattern=%s" % self.binding)
        return gl

    def stop(self):

        self.close()
        self._cbthread.join(timeout=5)
        self._cbthread.kill()
        self._cbthread = None
        log.info("ConversationSubscriber stopped. Conversation pattern=%s" % self.binding)

    def __str__(self):
        return "ConversationSubscriber callback: %s" % str(self._callback)


class ConvRepository(object):
    """
    Class that uses a data store to provide a persistent repository for ION events.
    """

    def __init__(self, datastore_manager=None):

        # Get an instance of datastore configured as directory.
        # May be persistent or mock, forced clean, with indexes
        datastore_manager = datastore_manager or bootstrap.container_instance.datastore_manager
        self.conv_store = datastore_manager.get_datastore(DataStore.DS_CONVERSATIONS, DataStore.DS_PROFILE.CONV)

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.conv_store.close()

    def put_conv(self, conv):
        log.debug("Store %s conversation persistently")
        if not isinstance(conv, ConversationMessage):
            raise BadRequest("conv must be type ConversationMessage, not %s" % type(conv))
        return self.conv_store.create(conv)

    def put_convs(self, convs):

        log.debug("Store %s conversation persistently", len(convs))
        if convs:
            if type(convs) is not list:
                raise BadRequest("Conversation must be type list, not %s" % type(convs))
            return self.conv_store.create_mult(convs)
        else:
            return None
