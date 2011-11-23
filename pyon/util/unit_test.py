#! /usr/bin/env pythoon
from mock import Mock, mocksignature, patch, DEFAULT
import unittest

from zope.interface import implementedBy

from pyon.service.service import get_service_by_name
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

class PyonTestCase(unittest.TestCase):

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

    def _create_service_mock(self, service_name):
        # set self.clients if not already set
        if getattr(self, 'clients', None) is None:
            setattr(self, 'clients', Mock(name='self.clients'))
        base_service = get_service_by_name(service_name)
        dependencies = base_service.dependencies
        for dep_name in dependencies:
            dep_service = get_service_by_name(dep_name)
            # Force mock service to use interface
            mock_service = Mock(name='self.clients.%s' % dep_name,
                    spec=dep_service)
            setattr(self.clients, dep_name, mock_service)
            # set self.dep_name for conevenience
            setattr(self, dep_name, mock_service)
            iface = list(implementedBy(dep_service))[0]
            names_and_methods = iface.namesAndDescriptions()
            for func_name, _ in names_and_methods:
                mock_func = mocksignature(getattr(dep_service, func_name),
                        mock=Mock(name='self.clients.%s.%s' % (dep_name,
                            func_name)), skipfirst=True)
                setattr(mock_service, func_name, mock_func)
