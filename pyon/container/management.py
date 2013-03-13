#!/usr/bin/env python

""" WELCOME to the home of container management

    This is a framework for performing administrative actions on a pycc container or a full distributed system of containers.

    A request is an event of type ContainerManagementRequest and contains a selector and an action.
    The selector is used to determine which containers the action should be performed on
    (or from the point of view of one container, if this action should be performed on this container).
    The action describes the change requested, and may be performed by one or more handlers.
    Handlers are registered with the system and can choose which actions they are able to perform.

    There is a peer relationship between IonObject subclasses ContainerManagementPredicate.
    The normal python object can be created from the peer by calling ContainerSelector.from_object(ion_object)
    and the Ion object can be created from the peer object by calling obj.get_peer()

    To maintain this relationship:
    1) the Ion object definition should include an (unused) peer attribute
       with decorators module (string name of the module containing the peer class) and class (optional string name of the peer class).
       If the class decorator is missing, the peer is assumed to have the same class name as the Ion object.
    2) the peer object class should define get_peer_class() (string name of Ion object type)
       and get_peer_args() (dictionary of attribute values for the Ion object)
"""

import sys
from threading import Lock

from ooi.logging import log, config
from pyon.ion.event import EventPublisher, EventSubscriber
from pyon.core.bootstrap import IonObject

from interface.objects import ContainerManagementRequest, ChangeLogLevel


# define selectors to determine if this message should be handled by this container.
# used by the message, manager should not interact with this directly

class ContainerSelector(object):
    """ base class for predicate classes to select which containers should handle messages
    """
    def __init__(self, peer):
        self.peer = peer
    def should_handle(self, container):
        raise Exception('subclass must override this method')
    def get_peer(self):
        return IonObject(self.get_peer_class(), **self.get_peer_args())
    def get_peer_class(self):
        return self.__class__.__name__
    def get_peer_args(self):
        return {}
    def __str__(self):
        return self.__class__.__name__

    @classmethod
    def from_object(cls, obj):
        """ get peer type from Ion object """
        mod = obj.get_decorator_value('peer', 'module')
        clazz = obj.get_decorator_value('peer', 'class') or obj.__class__.__name__
        subclass = getattr(sys.modules[mod], clazz)
        return subclass(obj)

class AllContainers(ContainerSelector):
    """ all containers should perform the action """
    def should_handle(self, container):
        return True

# TODO: more selectors
#class ContainersByName(ContainerSelector):
#class ContainersByIP(ContainerSelector):
#class ContainersRunningProcess(ContainerSelector):
#class ContainersInExecutionEngine(ContainerSelector):



# define types of messages that can be sent and handled

class EventHandler(object):
    """ base class for event handler objects registered to handle a particular type of container management action """
    def can_handle_request(self, action):
        raise Exception('subclass must implement this method')
    def handle_request(self, action):
        raise Exception('subclass must implement this method')
    def __str__(self):
        """ subclass should implement better name if behavior varies with args """
        return self.__class__.__name__

class LogLevelHandler(EventHandler):
    def can_handle_request(self, action):
        return isinstance(action, ChangeLogLevel)
    def handle_request(self, action):
        config.set_level(action.logger, action.level, action.recursive)

# TODO: other useful administrative actions
#    """ request that containers perform a thread dump """
#    """ request that containers log timing stats """
#    """ request that containers clear all timing stats """


# event listener to handle the messages

SEND_RESULT_IF_NOT_SELECTED=False # terrible idea... but might want for debug or audit?
DEFAULT_HANDLERS = [ LogLevelHandler() ]

class ContainerManager(object):
    def __init__(self, container, handlers=DEFAULT_HANDLERS):
        self.container = container
        self.running = False
        # make sure start() completes before an event is handled,
        # and any event is either handled before stop() begins,
        # or the handler begins after stop() completes and the event is dropped
        self.lock = Lock()
        self.handlers = handlers[:]

    def start(self):
        ## create queue listener and publisher
        self.sender = EventPublisher(event_type="ContainerManagementResult")
        self.receiver = EventSubscriber(event_type="ContainerManagementRequest", callback=self._receive_event)
        with self.lock:
            self.running = True
            self.receiver.start()
        log.info('ready for container management requests')

    def stop(self):
        log.debug('container management stopping')
        with self.lock:
            self.receiver.stop()
            self.sender.close()
            self.running = False
        log.debug('container management stopped')

    def add_handler(self, handler):
        self.handlers.append(handler)

    def _get_handlers(self, action):
        out = []
        for handler in self.handlers:
            if handler.can_handle_request(action):
                out.append(handler)
        return out

    def _receive_event(self, event, headers):
        with self.lock:
            if not isinstance(event, ContainerManagementRequest):
                log.trace('ignoring wrong type event: %r', event)
                return
            if not self.running:
                log.warn('ignoring admin message received after shutdown: %s', event.action)
                return
            predicate = ContainerSelector.from_object(event.predicate)
            if predicate.should_handle(self.container):
                log.trace('handling admin message: %s', event.action)
                self._perform_action(event.action)
            else:
                log.trace('ignoring admin action: %s', event.action)
                if SEND_RESULT_IF_NOT_SELECTED:
                    self.sender.publish_event(origin=self.container.id, action=event.action, outcome='not selected')
                    log.debug('received action: %s, outcome: not selected', event.action)

    def _perform_action(self, action):
        handlers = self._get_handlers(action)
        if not handlers:
            log.info('action accepted but no handlers found: %s', action)
            result = 'unhandled'
            self.sender.publish_event(origin=self.container.id, action=action, outcome=str(result))
            log.debug('received action: %s, outcome: %s', action, result)
        else:
            for handler in handlers:
                try:
                    result = handler.handle_request(action) or "completed"
                except Exception,e:
                    log.error("handler %r failed to perform action: %s", handler, action, exc_info=True)
                    result = e
                self.sender.publish_event(origin=self.container.id, action=action, outcome=str(result))
                log.debug('performed action: %s, outcome: %s', action, result)
