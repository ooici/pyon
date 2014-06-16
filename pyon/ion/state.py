#!/usr/bin/env python

"""State Repository implementation"""

__author__ = 'Michael Meisinger'

from pyon.core import bootstrap
from pyon.core.exception import NotFound, BadRequest, Conflict
from pyon.datastore.datastore import DataStore
from pyon.util.containers import get_ion_ts
from pyon.util.log import log

from interface.objects import ProcessState


class StateRepository(object):
    """
    Class that uses a data store to provide a persistent state repository for ION processes.
    """

    def __init__(self, datastore_manager=None, container=None):
        self.container = container or bootstrap.container_instance

        # Get an instance of datastore configured as directory.
        # May be persistent or mock, forced clean, with indexes
        datastore_manager = datastore_manager or self.container.datastore_manager
        self.state_store = datastore_manager.get_datastore("state", DataStore.DS_PROFILE.STATE)

    def start(self):
        pass

    def stop(self):
        self.close()

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.state_store.close()

    def put_state(self, key, state, state_obj=None):
        """
        Persist a private process state using the given key (typically a process id).
        The state vector is an object (e.g. a dict) that may contain any python type that
        is JSON-able. This means no custom objects are allowed in here.
        WARNING: If multiple threads/greenlets persist state concurrently, e.g. based
        on message processing and time, the calls to this method need to be protected
        by an exclusive lock (semaphore).
        @retval the ProcessState object as written
        """
        log.debug("Store persistent state for key=%s", key)
        if not isinstance(state, dict):
            raise BadRequest("state must be type dict, not %s" % type(state))
        if state_obj is not None:
            if not isinstance(state_obj, ProcessState):
                raise BadRequest("Argument state_obj is not ProcessState object")
            state_obj.state = state
            state_obj.ts = get_ion_ts()
            try:
                id, rev = self.state_store.update(state_obj)
                state_obj._rev = rev
                return state_obj
            except Conflict as ce:
                log.info("Process %s state update conflict - retry.")

        try:
            state_obj = self.state_store.read(key)
            state_obj.state = state
            state_obj.ts = get_ion_ts()
            id, rev = self.state_store.update(state_obj)
            state_obj._rev = rev
        except NotFound as nf:
            state_obj = ProcessState(state=state, ts=get_ion_ts())
            id, rev = self.state_store.create(state_obj, object_id=key)
            state_obj._id = id
            state_obj._rev = rev
        return state_obj

    def get_state(self, key):
        """
        Returns the state vector for given key (typically a process id).
        The state vector is a previously persisted object (e.g. a dict).
        In case no state was found, NotFound is raised.
        @retval a tuple with state vector and ProcessState object
        """
        log.debug("Retrieving persistent state for key=%s", key)
        state_obj = self.state_store.read(key)
        return state_obj.state, state_obj


class StatefulProcessMixin(object):
    """
    Mixin class for stateful processes.
    Need to avoid __init__
    """
    def _set_state(self, key, value):
        """
        Sets a key-value in the process's state vector. Marks the state as changed
        if the value has actually changed.
        """
        if not hasattr(self, "_proc_state"):
            self._proc_state = {}
            self._proc_state_changed = False

        old_state = self._proc_state.get(key, None)
        if old_state != value:
            self._proc_state[key] = value
            self._proc_state_changed = True
            log.debug("Process state updated. pid=%s, key=%s, value=%s", self.id, key, value)

    def _get_state(self, key, default=None):
        """
        Returns the value for a key from the process's state vector. If there is no
        value or the value is None, the default is returned.
        """
        if not hasattr(self, "_proc_state"):
            return None

        state = self._proc_state.get(key, None)
        return state if state is not None else default

    def _get_state_vector(self):
        """
        Returns the entire process state vector as a dict.
        Note: direct changes to the state vector will not automatically be detected.
        """
        if not hasattr(self, "_proc_state"):
            self._proc_state = {}
        return self._proc_state

    def _mark_changed(self):
        """
        Marks the process state vector as changed. The container will flush the
        state change to the repository when appropriate.
        """
        if not hasattr(self, "_proc_state"):
            self._proc_state = {}
        self._proc_state_changed = True

    def _flush_state(self):
        """
        Immediately pushes the state to the state repository. This call blocks
        until the write has completed
        """
        pass

    def _load_state(self):
        """
        Loads the process's state vector again from the state repository. Calling this
        operation should not be necessary in normal circumstances.
        """
        pass
