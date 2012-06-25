
from pyon.core.exception import *

from nose.plugins.attrib import attr
from unittest import TestCase
import traceback
from logging import DEBUG, INFO
from pyon.util.log import log, StackFormatter

@attr('UNIT')
class TestExceptionLogging(TestCase):

    def custom_stack_format(self, label, stack):
        self.formatter_was_called = True
        yield 'stack trace for ' + label


    def setUp(self):
        self.subject = log
        self.subject.set_stack_formatter('RPC')
        self.subject.setLevel(INFO)

    def testUsesFormatter(self):
        """ make sure our formatter method is getting used at the right times """
        self.formatter_was_called = False
        self.subject.set_stack_formatter(self.custom_stack_format)

        # logging with no exception does not call it
        self.subject.warning('message')
        self.assertFalse(self.formatter_was_called)
        #
        try:
            raise Exception('oh no!')
        except:
            self.subject.warning('message')
        self.assertFalse(self.formatter_was_called)
        #
        try:
            raise Exception('oh no!')
        except:
            self.subject.debug('message', exc_info=True)
        self.assertFalse(self.formatter_was_called)

        # logging non-Ion exception does not call formatter
        try:
            raise Exception('oh no!')
        except:
            self.subject.error('message', exc_info=True)
        self.assertFalse(self.formatter_was_called)

        # logging IonException with one stack does not call formatter
        try:
            raise IonException('oh no!')
        except:
            self.subject.error('message', exc_info=True)
        self.assertFalse(self.formatter_was_called)

        # logging IonException with multiple stacks does call formatter
        try:
            stack = traceback.extract_stack()
            e = IonException('oh no!')
            e.add_stack('second', stack)
            raise e
        except:
            self.subject.error('message', exc_info=True)
        self.assertTrue(self.formatter_was_called)

    def testFormat_notDropped(self):
        """ check that the RPC formatter drops the correct frames from the stack """
        def make_non_rpc(code='blah'):
            return ('non-rpc', 1, 'unused', code)
        def make_rpc(code='blah'):
            return ('path/pyon/net/endpoint.py', 1, 'unused', code)

        # stacks with too few sections
        stacks_missing_sections = [
            [ make_non_rpc() ],
            [ make_rpc() ],

            [ make_non_rpc(), make_rpc() ],
            [ make_non_rpc(), make_non_rpc() ],
            [ make_rpc(), make_non_rpc() ],
            [ make_rpc(), make_rpc() ],

            [ make_non_rpc(), make_non_rpc(), make_non_rpc() ],
            [ make_rpc(),     make_rpc(),     make_rpc() ],
            [ make_rpc(),     make_non_rpc(), make_non_rpc() ],
            [ make_non_rpc(), make_rpc(),     make_rpc() ],
            [ make_non_rpc(), make_rpc(),     make_non_rpc() ],
            [ make_non_rpc('drop'), make_non_rpc('drop'), make_rpc('drop'), make_rpc('drop'), make_non_rpc('keep') ]
        ]

        fmt = StackFormatter()._format_rpc_stack
        for stack in stacks_missing_sections:
            lines = [ line for line in fmt('label', stack) ]
            self.assertEqual(len(stack)+1, len(lines))


    def testFormat_drop_frames(self):
        """ check that the RPC formatter drops the correct frames from the stack """
        def make_non_rpc(code='blah'):
            return ('non-rpc', 1, 'unused', code)
        def make_rpc(code='blah'):
            return ('path/pyon/net/endpoint.py', 1, 'unused', code)

        # stacks with frames to drop at the top and bottom
        stacks_with_sections = [
            (1, [ make_non_rpc('drop'), make_non_rpc('drop'), make_rpc('drop'), make_rpc('drop'), make_non_rpc('keep'), make_rpc('drop') ]),
            (3, [ make_non_rpc('drop'), make_non_rpc('drop'), make_rpc('drop'), make_rpc('drop'), make_non_rpc('keep'), make_non_rpc('keep'), make_non_rpc('keep'), make_rpc('drop') ]),
            (3, [ make_non_rpc('drop'), make_non_rpc('drop'), make_rpc('drop'), make_rpc('drop'), make_non_rpc('keep'), make_rpc('keep'), make_non_rpc('keep'), make_rpc('drop') ]),
        ]

        fmt = StackFormatter()._format_rpc_stack
        for count,stack in stacks_with_sections:
            lines = [ line for line in fmt('label', stack) ]
            self.assertEqual(count+1, len(lines))
            for line in lines:
                self.assertFalse('drop' in line)



    def testFormat_drop_frames_initial(self):
        """ check that the RPC formatter drops the correct frames from the stack """
        def make_non_rpc(code='blah'):
            return ('non-rpc', 1, 'unused', code)
        def make_rpc(code='blah'):
            return ('path/pyon/net/endpoint.py', 1, 'unused', code)

        # stacks with frames to drop at the top and bottom
        stacks_with_sections = [
            (5, [ make_non_rpc('keep'), make_non_rpc('keep'), make_rpc('keep'), make_rpc('keep'), make_non_rpc('keep'), make_rpc('drop') ]),
            (7, [ make_non_rpc('keep'), make_non_rpc('keep'), make_rpc('keep'), make_rpc('keep'), make_non_rpc('keep'), make_non_rpc('keep'), make_non_rpc('keep'), make_rpc('drop') ]),
            (7, [ make_non_rpc('keep'), make_non_rpc('keep'), make_rpc('keep'), make_rpc('keep'), make_non_rpc('keep'), make_rpc('keep'), make_non_rpc('keep'), make_rpc('drop') ]),
            (1, [ make_non_rpc('keep'), make_rpc('drop'), make_rpc('drop') ]),
            (1, [ make_non_rpc('keep'), make_rpc('drop') ]),
            (2, [ make_non_rpc('keep'), make_non_rpc('keep'), make_rpc('drop'), make_rpc('drop'), make_non_rpc('drop') ])

        ]

        fmt = StackFormatter()._format_rpc_stack
        for count,stack in stacks_with_sections:
            lines = [ line for line in fmt('__init__', stack) ]
            self.assertEqual(count, len(lines), msg='did not drop to expected %d frames\nstack: %s\nformatted: %s' % (count,repr(stack), '\n'.join(lines)))
            for line in lines:
                self.assertFalse('drop' in line)
