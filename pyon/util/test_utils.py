#! /usr/bin/env pythoon
from mock import Mock, mocksignature, patch, DEFAULT
import unittest

from pyon.core.object import IonServiceRegistry

test_obj_registry = IonServiceRegistry()
test_obj_registry.register_obj_dir('obj/data')
test_obj_registry.register_svc_dir('obj/services')

def  pop_last_call(mock):
    if not mock.call_count:
        raise AssertionError('Cannot pop last call: call_count is 0')
    mock.call_args_list.pop()
    try:
        mock.call_args = mock.call_args_list[-1]
    except IndexError:
        mock.call_args = None
        mock.called = False
    mock.call_count -= 1

class PyonUnitTestCase(unittest.TestCase):

    # Call this function at the beginning of setUp if you need a mock ion
    # obj
    def _create_object_mock(self, name):
        mock_ionobj = Mock(name='IonObject')
        def side_effect(_def, _dict=None, **kwargs):
            test_obj = test_obj_registry.new(_def, _dict, **kwargs)
            test_obj._validate()
            return DEFAULT
        mock_ionobj.side_effect = side_effect
        patcher = patch(name, mock_ionobj)
        thing = patcher.start()
        self.addCleanup(patcher.stop)
        return thing

    def _create_service_mock(self, service_name, interface_base_class,
            func_name_list):
        try:
            self.clients
        except AttributeError:
            self.clients = Mock(name='self.clients')
        mock_service = self.clients.__getattr__(service_name)
        # set self.service_name
        self.__setattr__(service_name, mock_service)
        for func_name in func_name_list:
            mock_func = mocksignature(interface_base_class.__dict__[func_name],
                    mock=Mock(name='self.clients.%s.%s' % (service_name,
                        func_name)),
                    skipfirst=True)
            mock_service.__setattr__(func_name, mock_func)

class PyonIntegrationTestCase(PyonUnitTestCase):
    """
    Standard integration test case base class.
    """
