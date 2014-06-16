#!/usr/bin/env python

"""gevent-safe thread-local context as a mixin"""

__author__ = 'Dave Foster <dfoster@asascience.com>'


# note that this is only gevent-safe if monkey patched prior to importing this module
import threading
from contextlib import contextmanager

class LocalContextMixin(object):
    _lcm_context = None

    def __init__(self):
        self._lcm_context = threading.local()    # in gevent this is monkey patched to be a gevent.local

    @contextmanager
    def push_context(self, context):
        """
        Context Manager based context method.
        To use:
        with obj.push_context(context):
            # your operations while context is current
        # context resets to prior state here
        """
        cur_ctx = self.set_context(context)
        try:
            yield context
        finally:
            self.set_context(cur_ctx)

    def set_context(self, context):
        """
        Sets the "context" of this class.

        Used by Process level Endpoints (ProcessRPCClient, ProcessRPCServer) for propagating call context
        through service calls.

        @returns    The current context prior to this call. Should be used to push state.
        """
        cur_ctx = self.get_context()
        self._lcm_context.ctx = context
        return cur_ctx

    def get_context(self):
        """
        Gets the current "context" of this class.

        Used by Process level Endpoints (ProcessRPCClient, ProcessRPCServer) for propagating call context
        through service calls.

        If not set, returns None.
        """
        if hasattr(self._lcm_context, 'ctx'):
            return self._lcm_context.ctx
        return None