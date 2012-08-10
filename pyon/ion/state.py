#!/usr/bin/env python

"""State Repository implementation"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core import bootstrap
from pyon.core.exception import NotFound, BadRequest
from pyon.datastore.datastore import DataStore
from pyon.util.containers import get_ion_ts
from pyon.util.log import log

from interface.objects import ProcessState


class StateRepository(object):
    """
    Class that uses a data store to provide a persistent state repository for ION processes.
    """

    def __init__(self, datastore_manager=None):

        # Get an instance of datastore configured as directory.
        # May be persistent or mock, forced clean, with indexes
        datastore_manager = datastore_manager or bootstrap.container_instance.datastore_manager
        self.state_store = datastore_manager.get_datastore("state", DataStore.DS_PROFILE.STATE)

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.state_store.close()

    def put_state(self, key, state):
        log.debug("Store persistent state for key=%s" % key)
        if not isinstance(state, dict):
            raise BadRequest("state must be type dict, not %s" % type(state))
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

class StatefulProcessMixin(object):
    """
    Mixin class for stateful processes.
    Need to avoid __init__
    """

    def _set_state(self, key, value):
        if not hasattr(self, "_proc_state"):
            self._proc_state = {}
            self._proc_state_changed = False

        old_state = self._proc_state.get(key, None)
        if old_state != value:
            self._proc_state[key] = value
            self._proc_state_changed = True
            log.debug("Process state updated. pid=%s, key=%s, value=%s", self.id, key, value)

    def _get_state(self, key, default=None):
        if not hasattr(self, "_proc_state"):
            return None

        state = self._proc_state.get(key, None)
        return state if state is not None else default
