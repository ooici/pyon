#!/usr/bin/env python

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.public import log
from pyon.util.state_object import StateObject, BasicFSMFactory, BasicStates

import unittest

class StateObjectTest(unittest.TestCase):
    """
    Tests state object stuff
    """

    def test_SO(self):
        so = TestSO()
        self._assertCounts(so, 0, 0, 0, 0, 0)
        so._so_process(BasicStates.E_INITIALIZE)
        self._assertCounts(so, 1, 0, 0, 0, 0)
        so._so_process(BasicStates.E_ACTIVATE)
        self._assertCounts(so, 1, 1, 0, 0, 0)
        so._so_process(BasicStates.E_DEACTIVATE)
        self._assertCounts(so, 1, 1, 1, 0, 0)
        so._so_process(BasicStates.E_ACTIVATE)
        self._assertCounts(so, 1, 2, 1, 0, 0)
        so._so_process(BasicStates.E_DEACTIVATE)
        self._assertCounts(so, 1, 2, 2, 0, 0)
        so._so_process(BasicStates.E_TERMINATE)
        self._assertCounts(so, 1, 2, 2, 1, 0)

        # The following lead to errors
        so._so_process(BasicStates.E_INITIALIZE)
        self._assertCounts(so, 1, 2, 2, 1, 1)
        so._so_process(BasicStates.E_ACTIVATE)
        self._assertCounts(so, 1, 2, 2, 1, 2)
        so._so_process(BasicStates.E_DEACTIVATE)
        self._assertCounts(so, 1, 2, 2, 1, 3)
        so._so_process(BasicStates.E_TERMINATE)
        self._assertCounts(so, 1, 2, 2, 1, 4)

        so = TestSO()
        so._so_process(BasicStates.E_ACTIVATE)
        self._assertCounts(so, 0, 0, 0, 0, 1)

        so = TestSO()
        so._so_process(BasicStates.E_DEACTIVATE)
        self._assertCounts(so, 0, 0, 0, 0, 1)

        so = TestSO()
        so._so_process(BasicStates.E_TERMINATE)
        self._assertCounts(so, 0, 0, 0, 0, 1)

        so = TestSO()
        self._assertCounts(so, 0, 0, 0, 0, 0)
        res = so.initialize()
        self._assertCounts(so, 1, 0, 0, 0, 0)
        self.assertEqual(res, 33)
        so.activate()
        self._assertCounts(so, 1, 1, 0, 0, 0)
        so.deactivate()
        self._assertCounts(so, 1, 1, 1, 0, 0)

    def test_SO_error(self):
        # Tests error in state transition (not deferred) and error handler (not deferred)
        # Condition 1: error handler OK
        so = TestSO()
        self._assertCounts(so, 0, 0, 0, 0, 0)

        so.initialize()
        self._assertCounts(so, 1, 0, 0, 0, 0)
        try:
            so.activate(blow=True)
            self.fail("Exception expected")
        except RuntimeError, re:
            self.assertEqual(str(re),"blow")
        self._assertCounts(so, 1, 1, 0, 0, 1, 0)

        # Condition 2: error handler FAIL
        so = TestSO()
        so.initialize()
        try:
            so.activate(blow=True, errblow=True)
            self.fail("Exception expected")
        except RuntimeError, re:
            self.assertEqual(str(re),"errblow")
        self._assertCounts(so, 1, 1, 0, 0, 1, 1)

    def test_SO_argument(self):
        so = TestSO()
        so._so_process(BasicStates.E_INITIALIZE, 1, 2, 3)
        self._assertCounts(so, 1, 0, 0, 0, 0)
        self.assertEqual(so.args, (1, 2, 3))
        self.assertEqual(so.kwargs, {})
        so._so_process(BasicStates.E_ACTIVATE, a=1, b=2)
        self._assertCounts(so, 1, 1, 0, 0, 0)
        self.assertEqual(so.args, ())
        self.assertEqual(so.kwargs, dict(a=1, b=2))

        so = TestSO()
        so.initialize(1, 2, 3)
        self._assertCounts(so, 1, 0, 0, 0, 0)
        self.assertEqual(so.args, (1, 2, 3))
        self.assertEqual(so.kwargs, {})


    def test_SO_transition(self):
        so = TestSO()
        self._assertCounts(so, 0, 0, 0, 0, 0)
        so._so_process(BasicStates.E_INITIALIZE)
        self._assertCounts(so, 1, 0, 0, 0, 0)
        res1 = so._so_process(BasicStates.E_ACTIVATE)
        self._assertCounts(so, 1, 1, 0, 0, 0)
        self.assertEqual(res1, BasicStates.S_READY)

        so = TestSO()
        self._assertCounts(so, 0, 0, 0, 0, 0)
        so._so_process(BasicStates.E_INITIALIZE)
        self._assertCounts(so, 1, 0, 0, 0, 0)
        res2 = so._so_process(BasicStates.E_ACTIVATE,transition=True)
        self._assertCounts(so, 1, 1, 0, 0, 0)
        self.assertEqual(res2, BasicStates.S_ACTIVE)

        # make sure the current state of the object is still ACTIVE
        self.assertEqual(so._get_state(), BasicStates.S_ACTIVE)


    def _assertCounts(self, so, init, act, deact, term, error, errerr=0):
        self.assertEqual(so.cnt_init, init)
        self.assertEqual(so.cnt_act, act)
        self.assertEqual(so.cnt_deact, deact)
        self.assertEqual(so.cnt_term, term)
        self.assertEqual(so.cnt_err, error)
        self.assertEqual(so.cnt_errerr, errerr)


class TestLifecycleObject(StateObject):
    """
    A StateObject with a basic life cycle, as determined by the BasicFSMFactory.
    @see BasicFSMFactory
    @todo Add precondition checker
    """

    def __init__(self):
        StateObject.__init__(self)
        factory = BasicFSMFactory()
        fsm = factory.create_fsm(self)
        self._so_set_fsm(fsm)

    def initialize(self, *args, **kwargs):
        return self._so_process(BasicStates.E_INITIALIZE, *args, **kwargs)

    def activate(self, *args, **kwargs):
        return self._so_process(BasicStates.E_ACTIVATE, *args, **kwargs)

    def deactivate(self, *args, **kwargs):
        return self._so_process(BasicStates.E_DEACTIVATE, *args, **kwargs)

    def terminate(self, *args, **kwargs):
        return self._so_process(BasicStates.E_TERMINATE, *args, **kwargs)

    def error(self, *args, **kwargs):
        return self._so_process(BasicStates.E_ERROR, *args, **kwargs)

    def on_initialize(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_activate(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_deactivate(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_terminate_active(self, *args, **kwargs):
        """
        @brief this is a shorthand delegating to on_terminate from the ACTIVE
            state. Subclasses can override this action handler with more specific
            functionality
        """
        return self.on_terminate(*args, **kwargs)

    def on_terminate(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_error(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

class TestSO(TestLifecycleObject):
    def __init__(self):
        super(TestSO, self).__init__()
        self.cnt_init = 0
        self.cnt_act = 0
        self.cnt_deact = 0
        self.cnt_term = 0
        self.cnt_err = 0
        self.cnt_errerr = 0

    def on_initialize(self, *args, **kwargs):
        self.cnt_init += 1
        self.args = args
        self.kwargs = kwargs
        log.debug("on_initialize called")
        return 33

    def on_activate(self, *args, **kwargs):
        self.cnt_act += 1
        self.args = args
        self.kwargs = kwargs
        log.debug("on_activate called")
        if kwargs.get('transition', False):
            self._so_transition()
            return self._get_state()
        if kwargs.get('errblow', False):
            raise RuntimeError("errblow")
        if kwargs.get('blow', False):
            raise RuntimeError("blow")
        return self._get_state()

    def on_deactivate(self, *args, **kwargs):
        self.cnt_deact += 1
        self.args = args
        self.kwargs = kwargs
        log.debug("on_deactivate called")

    def on_terminate(self, *args, **kwargs):
        self.cnt_term += 1
        self.args = args
        self.kwargs = kwargs
        log.debug("on_terminate called")

    def on_error(self, *args, **kwargs):
        self.cnt_err += 1
        self.args = args
        self.kwargs = kwargs
        log.debug("on_error called")
        if len(args) == 0:
            # Case of illegal event error
            # @todo Distinguish
            return
        fail = args[0]
        if str(fail) == "errblow":
            self.cnt_errerr += 1
            raise RuntimeError("error error")
