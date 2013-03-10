#!/usr/bin/env python

"""Embedded (Gumstix) variant of the container with simplified implementations."""

__author__ = 'Michael Meisinger'

from pyon.container import ContainerCapability
from pyon.datastore.filestore.filestore import FileDataStore
from pyon.ion import resregistry
from pyon.ion.resregistry import ResourceRegistry


class EmbeddedResourceRegistryCapability(ContainerCapability):
    def __init__(self, container):
        self.container = container
        self._file_store = FileDataStore(container)
        self.container.resource_registry = None
        resregistry.EventPublisher = EmbeddedEventPublisherCapability

    def start(self):
        self.container.resource_registry = ResourceRegistry(datastore_manager=self, container=self.container)

    def get_datastore(self, *args, **kwargs):
        return self._file_store

class EmbeddedEventPublisherCapability(ContainerCapability):
    def __init__(self, container=None):
        self.container = container
        if self.container:
            self.container.event_pub = self

    def publish_event(self, *args, **kwargs):
        print "EventPublisher.publish_event", args, kwargs
