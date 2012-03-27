#!/usr/bin/env python

from pyon.core.exception import BadRequest
from pyon.util.log import log

"""
The appearance of the error and the log statement in a service is very important.

If all the log statements for the errors point to this class that is not good. The traceback must end at the calling class
not in pyon.util.arg_check!

"""


def assertEqual(a,b,message='a not equal b'):
    if a != b:
        raise(BadRequest(message))

def assertNotEqual(a, b, message='a is equal b'):
    pass

def assertTrue(x,message='x is not True'):
    pass

def assertIsInstance(a, b, message='a is not an instance of b'):
    pass

    """
    assertFalse(x)	bool(x) is False
    assertIs(a, b)	a is b	2.7
    assertIsNot(a, b)	a is not b	2.7
    assertIsNone(x)	x is None	2.7
    assertIsNotNone(x)	x is not None	2.7
    assertIn(a, b)	a in b	2.7
    assertNotIn(a, b)	a not in b	2.7
    assertIsInstance(a, b)	isinstance(a, b)	2.7
    assertNotIsInstance(a, b)	not isinstance(a, b)	2.7
    """


def foo(bar, baz, bish=None, bosh=67, bash='stuff'):


        assertEqual(bar,5)

        bish = bish or {}
        assertIsInstance(bish, dict)


foo('junk','jip')

