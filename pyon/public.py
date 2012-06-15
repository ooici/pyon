#!/usr/bin/env python

"""Entry point for importing common Pyon/ION packages. Most files should only need to import from here."""

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

__all__ = []


# Tell the magic import log setup to pass through this file
from pyon.util.log import import_paths
import_paths.append(__name__)

from pyon.util.log import log
__all__ += ['log']

from pyon.core.bootstrap import get_obj_registry, IonObject, get_sys_name, CFG
__all__ += ['get_obj_registry', 'IonObject', 'get_sys_name', 'CFG']

from pyon.core.object import ionprint
__all__ += ['ionprint']

from pyon.util.async import spawn, switch
__all__ += ['spawn', 'switch']

from pyon.core.thread import PyonThreadError, PyonThread, PyonThreadManager
__all__ += ['PyonThreadError', 'PyonThread', 'PyonThreadManager']

from pyon.core import exception as iex
__all__ += ['iex']

from pyon.net import messaging, channel, endpoint
__all__ += ['messaging', 'channel', 'endpoint']

from pyon.ion.process import IonProcessThreadManager, SimpleProcess, StandaloneProcess, ImmediateProcess
__all__ += ['IonProcessThreadManager', 'SimpleProcess', 'StandaloneProcess', 'ImmediateProcess']

from pyon.container.cc import Container
__all__ += ['Container']

from pyon.service.service import BaseService
__all__ += ['BaseService']

from pyon.ion.endpoint import ProcessRPCClient, ProcessRPCServer, ProcessSubscriber, ProcessPublisher
from pyon.ion.stream import StreamPublisher, StreamSubscriber, StreamSubscriberRegistrar, StreamPublisherRegistrar
__all__ += ['ProcessRPCClient', 'ProcessRPCServer', 'StreamPublisher', 'StreamSubscriber',
            'ProcessSubscriber', 'ProcessPublisher', 'StreamSubscriberRegistrar', 'StreamPublisherRegistrar']

from pyon.ion.resource import ResourceTypes, RT, ObjectTypes, OT,PredicateType, PRED, AssociationType, AT, LifeCycleStates, LCS, LCE
__all__ += ['RT', 'OT', 'PRED', 'AT', 'LCS', 'LCE']
__all__ += ['ResourceTypes', 'ObjectTypes', 'PredicateType', 'AssociationType', 'LifeCycleStates']

from pyon.ion.streamproc import StreamProcess
__all__ += ['StreamProcess']
