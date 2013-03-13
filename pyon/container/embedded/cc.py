#!/usr/bin/env python

"""Embedded (Gumstix) variant of the container with simplified implementations."""

__author__ = 'Michael Meisinger'

from pyon.container import ContainerCapability
from pyon.datastore.filestore.filestore import FileDataStore
from pyon.ion import resregistry
from pyon.ion.resregistry import ResourceRegistry


class EmbeddedResourceRegistryCapability(ContainerCapability):
    def __init__(self, container):
        ContainerCapability.__init__(self, container)
        self.container.resource_registry = None
        self._file_store = FileDataStore(container, datastore_name='resources')
        resregistry.EventPublisher = EmbeddedEventPublisherCapability

    def start(self):
        self._file_store.start()
        self.container.resource_registry = ResourceRegistry(datastore_manager=self, container=self.container)

    def stop(self):
        self._file_store.stop()
        self.container.resource_registry = None

    def get_datastore(self, *args, **kwargs):
        return self._file_store

class EmbeddedObjectStoreCapability(ContainerCapability):
    def __init__(self, container):
        ContainerCapability.__init__(self, container)
        self.container.object_store = None
        self._file_store = FileDataStore(container, datastore_name='objects')

    def start(self):
        self._file_store.start()
        self.container.object_store = self._file_store

    def stop(self):
        self._file_store.stop()
        self.container.object_store = None

class EmbeddedEventPublisherCapability(ContainerCapability):
    def __init__(self, container=None):
        ContainerCapability.__init__(self, container)
        if self.container:
            self.container.event_pub = self

    def publish_event(self, *args, **kwargs):
        print "EventPublisher.publish_event", args, kwargs
