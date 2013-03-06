__author__ = 'rn710'
import unittest
from pyon.core.governance.conversation.core.fsm import FSM
from pyon.core.governance.conversation.core.fsm import ExceptionFSM
from collections import deque
from pyon.util.unit_test import PyonTestCase
from pyon.util.log import log
from nose.plugins.attrib import attr

def dummy_action(fsm):
    log.debug('I have been called')

def toDeque(alist):
    return [deque(l) for l in alist]

@attr('UNIT')
class TestFSM(PyonTestCase):
    def get_test_fsm(self):
        # build test data
        testData = FSM('1_1')
        testData.state_transitions = {('a', '1_1'):(None, None, '1_2')}
        return testData

    def test_add_fsm_to_state_when_memory_is_empty(self):
        fsm = FSM(1)
        nested_fsm = FSM('1_1')
        fsm.add_fsm_to_memory(1, nested_fsm)

        log.debug("test_add_fsm_to_state_when_memory_is_empty: %s" , fsm.memory)
        self.assertEqual(fsm.memory.get(1), [nested_fsm])

    def test_add_fsm_to_state_that_is_already_in_memory(self):
        fsm = FSM(1)
        first_fsm = self.get_test_fsm()
        fsm.memory = {1: [first_fsm]}
        second_fsm = self.get_test_fsm()
        fsm.add_fsm_to_memory(1,second_fsm)
        log.debug("test_add_fsm_to_state_that_is_already_in_memory%s" ,fsm.memory)

        self.assertEqual(len(fsm.memory),1)
        self.assertEqual(fsm.memory.get(1), [first_fsm, second_fsm])

    def test_add_fsm_to_state_that_is_not_in_memory_and_memory_is_not_empty(self):
        fsm = FSM(1)
        first_fsm = self.get_test_fsm()
        fsm.memory = {1: [first_fsm]}
        second_fsm = self.get_test_fsm()
        fsm.add_fsm_to_memory(2,second_fsm)
        log.debug('test_add_fsm_to_state_that_is_not_in_memory_and_memory_is_not_empty: %s', fsm.memory)
        self.assertEqual(len(fsm.memory),2)
        self.assertEqual(fsm.memory.get(1), [first_fsm])
        self.assertEqual(fsm.memory.get(1), [second_fsm])

    def test_get_transition_from_memory_when_there_is_a_match(self):
        fsm = FSM(1)
        first_fsm = self.get_test_fsm()
        fsm.memory = {1: [first_fsm]}

        (_, _, next_state) = fsm.get_transition('a', 1)
        self.assertEqual(next_state,1)
        self.assertEqual(fsm.memory.get(1),[first_fsm])

    def test_get_normal_transition_when_there_is_a_match(self):
        fsm = FSM(1)
        fsm.state_transitions = {('b', 1):(None, None, 2)}
        first_fsm = self.get_test_fsm()
        fsm.memory = {2: [first_fsm]}

        (_, _, next_state) = fsm.get_transition('b', 1)
        self.assertEqual(next_state,2)
        self.assertEqual(fsm.memory.get(2),[first_fsm])

    def test_get_normal_transition_when_there_is_no_match(self):
        fsm = FSM(1)
        fsm.state_transitions = {('b', 1):(None, None, 2)}
        first_fsm = self.get_test_fsm()
        fsm.memory = {2: [first_fsm]}
        self.assertRaises(ExceptionFSM, fsm.get_transition, 'c', 1)

    def test_get_normal_transition_when_there_is_no_match_but_such_transition_exist(self):
        fsm = FSM(1)
        #fsm.state_transitions = {('b', 1):(None, 2)}
        first_fsm = FSM('1_1')
        first_fsm.state_transitions = {('a', '1_1'):(None, None, '1_2'), (fsm.END_PAR_TRANSITION, '1_2'): (None, None, 2)}
        fsm.memory = {2: [first_fsm]}
        (_, _, next_state) = fsm.get_transition( 'a', 2)
        log.debug("test_get_normal_transition_when_there_is_no_match_but_such_transition_exist:%s", fsm.memory)
        self.assertEqual(fsm.memory, {2:[]})
        self.assertEqual(next_state, 2)
"""
def test_nested_transition_for_first_time(self):
    # Test set_up
    fsm = FSM(1)
    nested_fsm = FSM('1_1')
    fsm.memory = {1: [nested_fsm]}

    # build test data
    testData = self.get_test_fsm()


    fsm.add_nested_transition('a', 1, '1_1', '1_2', None, None)
    log.debug("test_nested_transition_for_first_time: %s", fsm.memory)
    self.assertEqual(fsm.memory.get(1), [testData])
    """