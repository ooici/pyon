#!/usr/bin/env python

from pyon.net.channel import BaseChannel, SendChannel, RecvChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel, ChannelError, ChannelShutdownMessage, ListenChannel, PublisherChannel
from gevent import queue, spawn
from pyon.util.unit_test import PyonTestCase
from mock import Mock, sentinel, patch
from pika import channel as pchannel
from pika import BasicProperties
from nose.plugins.attrib import attr
from pyon.net.transport import NameTrio, BaseTransport
from pyon.util.fsm import ExceptionFSM
from pyon.util.int_test import IonIntegrationTestCase
import time
from gevent.event import Event
import Queue as PQueue
from gevent.queue import Queue
from unittest import skip
from pyon.core import bootstrap

@attr('UNIT')
class TestConversation(PyonTestCase):
    pass

class TestPrincipal(PyonTestCase):
    pass
