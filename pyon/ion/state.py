#!/usr/bin/env python

"""State Repository implementation"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import IonObject, CFG
from pyon.core.exception import Conflict, NotFound, BadRequest
from pyon.datastore.datastore import DataStore, DatastoreManager
from pyon.util.containers import get_ion_ts
from pyon.util.log import log

from interface.objects import ProcessState


class StateRepository(object):
    """
    Singleton class that uses a data store to provide a persistent state repository for ION processes.
    """

    # Storage for the instance reference
    __instance = None

    @classmethod
    def get_instance(cls):
        """
        Create singleton instance
        """
        if StateRepository.__instance is None:
            StateRepository.__instance = "NEW"
            # Create and remember instance
            StateRepository.__instance = StateRepository()
        return StateRepository.__instance

    def __init__(self):
        assert StateRepository.__instance == "NEW", "Cannot instantiate StateRepository multiple times"

        # Get an instance of datastore configured as directory.
        # May be persistent or mock, forced clean, with indexes
        self.state_store = DatastoreManager.get_datastore("state", DataStore.DS_PROFILE.STATE)

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.state_store.close()

    def put_state(self, key, state):
        log.debug("Store persistent state for key=%s" % key)
        if not isinstance(state, dict):
            raise BadRequest("state must by type dict, not %s" % type(state))
        try:
            state_obj = self.state_store.read(key)
            state_obj.state = state
            state_obj.ts = get_ion_ts()
            self.state_store.update(state_obj)
        except NotFound as nf:
            state_obj = ProcessState(state=state, ts=get_ion_ts())
            self.state_store.create(state_obj, object_id=key)

    def get_state(self, key):
        log.debug("Retrieving persistent state for key=%s" % key)
        state_obj = self.state_store.read(key)
        return state_obj.state
