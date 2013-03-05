""" WELCOME to the home of container management

    This is a framework for performing administrative actions on a pycc container or a full distributed system of containers.
    The actions are some subclass of type AdminRequest and always include a container_selector attribute.
    The container_selector decides which containers should perform this action on a distributed system,
    and are some subclass of ContainerSelector.

    ContainerManagementRequestEvent objects are used to pass requests throughout the system and
    the ContainerManagementListener listens for and handles these events.
    After performing the requested action, the container will emit a ContainerManagementEvent with the result.

    AdminRequests are serializable as string values.
    In particular, for any AdminRequest x, the implementation must guarantee that:
        AdminRequest.from_string( str(x) ) == x
    This serialization simplifies passing requests in URLs.
"""

import sys
import logging
from ooi.logging import log, config
from pyon.event.event import EventPublisher, EventSubscriber
from pyon.core.exception import BadRequest
from interface.objects import ContainerManagementRequestEvent
from threading import Lock

# define selectors to determine if this message should be handled by this container.
# used by the message, manager should not interact with this directly

class ContainerSelector(object):
    """ base class for predicate classes to select which containers should handle messages

        subclasses can be represented as string values so that for any ContainerSelector x:
            x == ContainerSelector.from_string( str(x) )

        to implement this, any subclass must define str(x) as classname,details[,more_details...]
        and provide a constructor classname(*details)
        or if no details are needed, str(x) should be classname and define a no-arg constructor (both are already defaults)
    """
    def should_handle(self, container):
        raise Exception('subclass must override this method')
    def _from_string(self, parts):
        """ configure from string value """
        pass # default action is do nothing
    def __str__(self):
        return self.__class__.__name__
    @classmethod
    def from_string(cls, value):
        parts = value.split(',')
        subclass = getattr(sys.modules[__name__], parts[0])
        return subclass(persist=parts[1:]) if len(parts)>1 else subclass()

class AllContainers(ContainerSelector):
    """ all containers should perform the action """
    def should_handle(self, container):
        return True
    def __eq__(self, other):
        return isinstance(other, AllContainers)

ALL_CONTAINERS=AllContainers()

# TODO: more selectors
#class ContainersByName(ContainerSelector):
#    """ specific list of containers """
#    def __init__(self, name_list):
#        self.names = name_list.split(',')
#    def should_handle(self,container):
#        name = container.get_name() ??
#        return name in self.names
#class ContainersByIP(ContainerSelector):
#    pass



# define types of messages that can be sent and handled

class AdminRequest(object):
    """ base class for messages

        subclasses can be represented as string values so that for any ContainerSelector x:
            x == ContainerSelector.from_string( str(x) )

        to implement this, any subclass must define str(x) as classname:details[:more_details...]
        and provide a constructor classname(persist=[details,...])
        or if no details are needed, str(x) should be classname and define a no-arg constructor (both are already defaults)

        representation as a string is needed so requests can be passed in a URL to the service gateway
    """
    def __init__(self, container_selector=ALL_CONTAINERS):
        self.container_selector = container_selector
    def perform_action(self, container):
        raise Exception('subclass must override this method')
    def should_handle(self, container):
        return self.container_selector.should_handle(container)
    def __str__(self):
        return "%s:%s" % (self.__class__.__name__, self.container_selector)

    @classmethod
    def from_string(cls, value):
        parts = value.split(':')
        subclass = getattr(sys.modules[__name__], parts[0])
        selector = ContainerSelector.from_string(parts[1])
        return subclass(container_selector=selector, persist=parts[2:]) if len(parts)>2 else subclass(container_selector=selector)

class LogAdmin(AdminRequest):
    """ message to request a change in log levels """
    def __init__(self, container_selector=None, logger=None, level=None, recursive=None, persist=None):
        super(LogAdmin,self).__init__(container_selector)
        if level:
            # configure from individual args
            self.logger = logger
            self.recursive = recursive
            self.level = level if isinstance(level, str) else logging.getLevelName(level)
        else:
            # configure from string
            if len(persist)!=3:
                raise BadRequest('expected exactly three string arguments: %r' % persist)
            self.recursive = persist[2]=='True'
            self.logger = persist[0]
            self.level = persist[1]
    def perform_action(self, container):
        log.info('changing log level: %s: %s', self.logger, logging.getLevelName(self.level))
        config.set_level(self.logger, self.level, self.recursive)
        return "updated"
    def __str__(self):
        return "%s:%s:%s:%s" % (super(LogAdmin,self).__str__(), self.logger, self.level, self.recursive)
    def __eq__(self, other):
        return isinstance(other, LogAdmin) and self.level==other.level and self.logger==other.logger and self.recursive==other.recursive

# TODO: other useful administrative actions
#
#class ThreadDump(AdminRequest):
#    """ request that containers perform a thread dump """
#    pass
#
#class LogTimingStats(AdminRequest):
#    """ request that containers log timing stats """
#    pass
#
#class ResetTimingStats(AdminRequest):
#    """ request that containers clear all timing stats """
#    pass




# event listener to handle the messages

class ContainerManager(object):
    def __init__(self, container):
        self.container = container
        self.running = False
        # make sure start() completes before an event is handled,
        # and any event is either handled before stop() begins,
        # or the handler begins after stop() completes and the event is dropped
        self.lock = Lock()
    def start(self):
        ## create queue listener and publisher
        self.sender = EventPublisher(event_type="ContainerManagementEvent")
        self.receiver = EventSubscriber(event_type="ContainerManagementRequestEvent", callback=self.process_event)
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
    def process_event(self, event, headers):
        with self.lock:
            if not isinstance(event, ContainerManagementRequestEvent):
                log.trace('ignoring wrong type event: %r', event)
                return
            request = event.request if isinstance(event.request,AdminRequest) else AdminRequest.from_string(event.request)
            if not self.running:
                log.warn('ignoring admin message received after shutdown: %s', request)
                return
            if request.should_handle(self.container):
                log.trace('handling admin message: %s', request)
                self._perform_action(request)
            else:
                log.trace('ignoring admin request: %s', request)
    def _perform_action(self, request):
        try:
            result = request.perform_action(self.container)
        except Exception,e:
            log.error("operation failed: %s", e, exc_info=True)
            result = e
        self.sender.publish_event(origin=self.container.id, request=str(request), outcome=str(result))
        log.debug('performed request: %s, outcome: %s', request, result)
