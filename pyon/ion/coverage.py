#!/usr/bin/env python

"""Coverage Postgres Table implementation"""

__author__ = 'Casey Bryant'

from pyon.core import bootstrap
from pyon.datastore.datastore import DataStore


class CoverageMetadataStore(object):
    """
    Class that uses a data store to provide a persistent repository for coverage-model metadata.
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
