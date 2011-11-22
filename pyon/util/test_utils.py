#! /usr/bin/env pythoon
from mock import Mock, mocksignature, patch
import unittest

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
    def _create_patch(self, name):
        patcher = patch(name)
        thing = patcher.start()
        self.addCleanup(patcher.stop)
        return thing

    def _create_service_mock(self, service_name, interface_base_class,
            func_name_list):
        try:
            self.mock_clients
        except AttributeError:
            self.mock_clients = Mock(name='self.clients')
        mock_service = self.mock_clients. __getattr__(service_name)
        for func_name in func_name_list:
            mock_func = mocksignature(interface_base_class.__dict__[func_name],
                    mock=Mock(name='mock_' + func_name),
                    skipfirst=True)
            self.__setattr__('mock_' + func_name, mock_func)
            mock_service.__setattr__(func_name, mock_func)
