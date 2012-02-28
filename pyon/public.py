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

from pyon.util.config import CFG
__all__ += ['CFG']

from pyon.core.bootstrap import obj_registry, IonObject, get_sys_name
sys_name = get_sys_name()
__all__ += ['obj_registry', 'IonObject', 'sys_name']

from pyon.core.object import ionprint
__all__ += ['ionprint']

from pyon.util.async import spawn, switch
__all__ += ['spawn', 'switch']

from pyon.core.process import PyonProcessError, GreenProcess, GreenProcessSupervisor, PythonProcess
__all__ += ['PyonProcessError', 'GreenProcess', 'GreenProcessSupervisor', 'PythonProcess']

from pyon.core import exception as iex
__all__ += ['iex']

from pyon.net import messaging, channel, endpoint
__all__ += ['messaging', 'channel', 'endpoint']

from pyon.ion.process import IonProcessSupervisor, SimpleProcess, StandaloneProcess, ImmediateProcess
__all__ += ['IonProcessSupervisor', 'SimpleProcess', 'StandaloneProcess', 'ImmediateProcess']

from pyon.container.cc import Container
__all__ += ['Container']

from pyon.service.service import BaseService
__all__ += ['BaseService']

from pyon.ion.endpoint import ProcessRPCClient, ProcessRPCServer, StreamPublisher, StreamSubscriber, \
                                ProcessSubscriber, ProcessPublisher, StreamSubscriberRegistrar, StreamPublisherRegistrar
__all__ += ['ProcessRPCClient', 'ProcessRPCServer', 'StreamPublisher', 'StreamSubscriber',
            'ProcessSubscriber', 'ProcessPublisher', StreamSubscriberRegistrar, StreamPublisherRegistrar]

from pyon.ion.resource import ResourceTypes, RT, PredicateType, PRED, AssociationType, AT, LifeCycleStates, LCS, LCE
__all__ += ['RT', 'PRED', 'AT', 'LCS', 'LCE']
__all__ += ['ResourceTypes', 'PredicateType', 'AssociationType', 'LifeCycleStates']

from pyon.ion.streamproc import StreamProcess
__all__ += ['StreamProcess']
