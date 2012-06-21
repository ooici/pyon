
from pyon.core.exception import *

from nose.plugins.attrib import attr
from unittest import TestCase
import traceback

@attr('UNIT')
class TestExceptionUtils(TestCase):
    def setUp(self):
        self.subject = ExceptionFactory()
    def tearDown(self):
        self.subject = None

    def testCreateException(self):
        ex = self.subject.create_exception(553, 'test message')
        self.assertEqual(553, ex.status_code)
        self.assertEqual('test message', ex.message)
        self.assertTrue(isinstance(ex, ContainerStartupError))

        try:
            raise ex
            fail('should be unreachable')
        except ContainerStartupError:
            pass
        except:
            fail('should have caught this above')

    def testCreateWithStack(self):
        stack = traceback.extract_stack()
        ex = self.subject.create_exception(553, 'test2 message', {'added': stack})
        self.assertEqual(553, ex.status_code)
        self.assertEqual('test2 message', ex.message)
        d = ex.get_stacks()
        self.assertTrue('__init__' in d)
        self.assertTrue('added' in d)
        self.assertTrue(isinstance(d['__init__'],list))

    def testToString(self):
        stack = self.get_stack(3)
        ex = self.subject.create_exception(553, 'test2 message', {'added': stack})
        msg1 = ex.format_stack()
        msg2 = ex.format_stack(filter=self.show_frame)
        self.assertTrue(len(msg1)>len(msg2))

    def get_stack(self, n):
        if n>0:
            return self.get_stack(n-1)
        else:
            return traceback.extract_stack()

    def show_frame(self, label, file, line, caller, code):
        return label=='__init__'