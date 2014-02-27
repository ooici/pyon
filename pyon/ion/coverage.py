#!/usr/bin/env python

"""State Repository implementation"""

__author__ = 'Casey Bryant'
__license__ = 'Apache 2.0'

from pyon.core import bootstrap
from pyon.core.exception import NotFound, BadRequest, Conflict
from pyon.datastore.datastore import DataStore
from pyon.util.containers import get_ion_ts
from pyon.util.log import log

from interface.objects import ProcessState


class CoverageMetadataStore(object):
    """
    Class that uses a data store to provide a persistent state repository for ION processes.
    """

    def __init__(self, datastore_manager=None, container=None):
        self.container = container or bootstrap.container_instance

        # Get an instance of datastore configured as directory.
        # May be persistent or mock, forced clean, with indexes
        datastore_manager = datastore_manager or self.container.datastore_manager
        self.coverage_store = datastore_manager.get_datastore("coverage", DataStore.DS_PROFILE.COVERAGE)

    def start(self):
        pass

    def stop(self):
        self.close()

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.coverage_store.close()
