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
