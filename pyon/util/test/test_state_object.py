#!/usr/bin/env python

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.util.state_object import LifecycleStateMixin
from pyon.util.int_test import IonIntegrationTestCase

class StateObjectTest(IonIntegrationTestCase):
    """
    Tests state object stuff
    """

    def test_SO(self):
        so = TestSO()
        self._assertCounts(so, 0, 0, 0, 0, 0)
        so._smprocess(LifecycleStateMixin.E_INIT)
        self._assertCounts(so, 1, 0, 0, 0, 0)
        so._smprocess(LifecycleStateMixin.E_START)
        self._assertCounts(so, 1, 1, 0, 0, 0)
        so._smprocess(LifecycleStateMixin.E_STOP)
        self._assertCounts(so, 1, 1, 1, 0, 0)
        so._smprocess(LifecycleStateMixin.E_START)
        self._assertCounts(so, 1, 2, 1, 0, 0)
        so._smprocess(LifecycleStateMixin.E_STOP)
        self._assertCounts(so, 1, 2, 2, 0, 0)
        so._smprocess(LifecycleStateMixin.E_QUIT)
        self._assertCounts(so, 1, 2, 2, 1, 0)

        # The following lead to errors
        so._smprocess(LifecycleStateMixin.E_INIT)
        self._assertCounts(so, 1, 2, 2, 1, 1)
        so._smprocess(LifecycleStateMixin.E_START)
        self._assertCounts(so, 1, 2, 2, 1, 2)
        so._smprocess(LifecycleStateMixin.E_STOP)
        self._assertCounts(so, 1, 2, 2, 1, 3)
        so._smprocess(LifecycleStateMixin.E_QUIT)
        self._assertCounts(so, 1, 2, 2, 1, 4)

        so = TestSO()
        so._smprocess(LifecycleStateMixin.E_START)
        self._assertCounts(so, 0, 0, 0, 0, 1)

        so = TestSO()
        so._smprocess(LifecycleStateMixin.E_STOP)
        self._assertCounts(so, 0, 0, 0, 0, 1)

        so = TestSO()
        so._smprocess(LifecycleStateMixin.E_QUIT)
        self._assertCounts(so, 0, 0, 0, 0, 1)

        so = TestSO()
        self._assertCounts(so, 0, 0, 0, 0, 0)
        res = so.init()
        self._assertCounts(so, 1, 0, 0, 0, 0)
        self.assertEqual(res, 33)
        so.start()
        self._assertCounts(so, 1, 1, 0, 0, 0)
        so.stop()
        self._assertCounts(so, 1, 1, 1, 0, 0)

    def xtest_SO_error(self):
        # Tests error in state transition (not deferred) and error handler (not deferred)
        # Condition 1: error handler OK
        so = TestSO()
        self._assertCounts(so, 0, 0, 0, 0, 0)

        so.init()
        self._assertCounts(so, 1, 0, 0, 0, 0)
        try:
            so.start(blow=True)
            self.fail("Exception expected")
        except RuntimeError, re:
            self.assertEqual(str(re),"blow")
        self._assertCounts(so, 1, 1, 0, 0, 1, 0)

        # Condition 2: error handler FAIL
        so = TestSO()
        so.init()
        try:
            so.start(blow=True, errblow=True)
            self.fail("Exception expected")
        except RuntimeError, re:
            self.assertEqual(str(re),"errblow")
        self._assertCounts(so, 1, 1, 0, 0, 1, 1)

    def test_SO_argument(self):
        so = TestSO()
        so._smprocess(LifecycleStateMixin.E_INIT, 1, 2, 3)
        self._assertCounts(so, 1, 0, 0, 0, 0)
        self.assertEqual(so.args, (1, 2, 3))
        self.assertEqual(so.kwargs, {})
        so._smprocess(LifecycleStateMixin.E_START, a=1, b=2)
        self._assertCounts(so, 1, 1, 0, 0, 0)
        self.assertEqual(so.args, ())
        self.assertEqual(so.kwargs, dict(a=1, b=2))

        so = TestSO()
        so.init(1, 2, 3)
        self._assertCounts(so, 1, 0, 0, 0, 0)
        self.assertEqual(so.args, (1, 2, 3))
        self.assertEqual(so.kwargs, {})


    def test_SO_transition(self):
        so = TestSO()
        self._assertCounts(so, 0, 0, 0, 0, 0)
        so._smprocess(LifecycleStateMixin.E_INIT)
        self._assertCounts(so, 1, 0, 0, 0, 0)
        res1 = so._smprocess(LifecycleStateMixin.E_START)
        self._assertCounts(so, 1, 1, 0, 0, 0)
        self.assertEqual(res1, LifecycleStateMixin.S_READY)

        so = TestSO()
        self._assertCounts(so, 0, 0, 0, 0, 0)
        so._smprocess(LifecycleStateMixin.E_INIT)
        self._assertCounts(so, 1, 0, 0, 0, 0)
        res2 = so._smprocess(LifecycleStateMixin.E_START,transition=True)
        self._assertCounts(so, 1, 1, 0, 0, 0)
        self.assertEqual(res2, LifecycleStateMixin.S_ACTIVE)

        # make sure the current state of the object is still ACTIVE
        self.assertEqual(so._state, LifecycleStateMixin.S_ACTIVE)


    def _assertCounts(self, so, init, act, deact, term, error, errerr=0):
        self.assertEqual(so.cnt_init, init)
        self.assertEqual(so.cnt_act, act)
        self.assertEqual(so.cnt_deact, deact)
        self.assertEqual(so.cnt_term, term)
        self.assertEqual(so.cnt_err, error)
        self.assertEqual(so.cnt_errerr, errerr)


class TestLifecycleObject(LifecycleStateMixin):
    """
    A StateObject with a basic life cycle, as determined by the BasicFSMFactory.
    @see BasicFSMFactory
    @todo Add precondition checker
    """

    def init(self, *args, **kwargs):
        return self._smprocess(LifecycleStateMixin.E_INIT, *args, **kwargs)

    def start(self, *args, **kwargs):
        return self._smprocess(LifecycleStateMixin.E_START, *args, **kwargs)

    def stop(self, *args, **kwargs):
        return self._smprocess(LifecycleStateMixin.E_STOP, *args, **kwargs)

    def quit(self, *args, **kwargs):
        return self._smprocess(LifecycleStateMixin.E_QUIT, *args, **kwargs)

    def error(self, *args, **kwargs):
        return self._smprocess(LifecycleStateMixin.E_ERROR, *args, **kwargs)

    def on_init(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_start(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_stop(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_quit(self, *args, **kwargs):
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

    def on_init(self, *args, **kwargs):
        self.cnt_init += 1
        self.args = args
        self.kwargs = kwargs
        log.debug("on_init called")
        return 33

    def on_start(self, *args, **kwargs):
        self.cnt_act += 1
        self.args = args
        self.kwargs = kwargs
        log.debug("on_start called")
        if kwargs.get('transition', False):
            self._smtransition()
            return self._state
        if kwargs.get('errblow', False):
            raise RuntimeError("errblow")
        if kwargs.get('blow', False):
            raise RuntimeError("blow")
        return self._state

    def on_stop(self, *args, **kwargs):
        self.cnt_deact += 1
        self.args = args
        self.kwargs = kwargs
        log.debug("on_stop called")

    def on_quit(self, *args, **kwargs):
        self.cnt_term += 1
        self.args = args
        self.kwargs = kwargs
        log.debug("on_quit called")

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
