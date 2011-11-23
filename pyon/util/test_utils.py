#!/usr/bin/env python

__author__ = 'Jamie Chen'
__license__ = 'Apache 2.0'


from mock import Mock, mocksignature, patch
import unittest

def pop_last_call(mock):
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
    """
    Base class for all Pyon unit tests
    """
    def _create_patch(self, name):
        patcher = patch(name)
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
    Base class for all Pyon integration tests
    """
