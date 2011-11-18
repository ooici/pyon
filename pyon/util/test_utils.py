#! /usr/bin/env pythoon
from mock import Mock
from contextlib import contextmanager

@contextmanager
def switch_ref(module_name, attribute_name):
    '''Assuming there is __dict__'''
    __import__(module_name)
    import sys
    module = sys.modules[module_name]
    real = module.__dict__[attribute_name]
    mock = Mock()
    module.__dict__[attribute_name] = mock
    yield mock
    module.__dict__[attribute_name] = real
