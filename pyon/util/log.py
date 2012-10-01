"""
logging utilities for pycc container
- formatter that makes RPC exception chains more readable by dropping the RPC communication-related overhead (pyon.endpoint, pika, gevent, etc)
- log, the magic scoped logger anyone can import (now with TRACE log level)
- config, the log configuration manager
"""

import ooi.logging
import ooi.logging.format
import logging
import sys

log = ooi.logging.log

TRACE = 'TRACE'
DEBUG     = 'DEBUG'
INFO      = 'INFO'
WARNING   = 'WARNING'
ERROR     = 'ERROR'
CRITICAL  = 'CRITICAL'
EXCEPTION = 'EXCEPTION'

class RPCStackFormatter(ooi.logging.format.StackFormatter):
    """ print stack traces for exceptions with special handling for chains of RPC calls.
        for chains of RPC calls, the stack trace will drop stack frames from the top (where gevent invokes the function),
        and from the bottom (where the call invokes another remote RPC service and passes through the broker).
        the intent is that the frames show only application business logic and not the details of relaying through RPC.
        this is appropriate for tracing application issues if the RPC framework code is trusted.
        when troubleshooting the RPC framework, use StackFormatter or the default logging formatter instead.

        USAGE

        Example lines from logging.yml:

            formatters:
              rpc:
                (): 'pyon.util.log.RPCStackFormatter'
                format: '%(asctime)s %(levelname)-8s %(threadName)s %(name)-15s:%(lineno)d %(message)s'
            handlers:
              console:
                class: logging.StreamHandler
                level: DEBUG
                stream: ext://sys.stdout
                formatter: rpc
    """
    def filter_frames(self, top_stack, stack):
        # split stack into sections.
        # if this is the first stack, sections will be: displayable, endpoint, non-endpoint
        # otherwise the sections will be: non-endpoint, endpoint, displayable, endpoint, non-endpoint
        #
        # if it matches this pattern, return only the middle "displayable" section,
        # otherwise return the whole stack.
        #
        # "endpoint" means pyon.net.endpoint or pyon.ion.endpoint
        # "non-endpoint" means anything else, although TODO: should limit this to non-project code only (like pika, gevent, ...)
        #
        # TODO: make sections and definitions of sections configurable to keep up with code changes, apply to other uses
        #
        have_required_sections = False
        display_frames = []
        if not stack:
            return display_frames
        finished_iterating = False
        i = iter(stack)
        try:
            file,line,method,code = i.next()

            if not top_stack:
                # ignore one section of non-endpoint (greenlet invocation, etc), then one section of RPC
                _, file,line,method,code = self._collect_frames(False, i, file,line,method,code)
                _, file,line,method,code = self._collect_frames(True, i, file,line,method,code)

            # keep collecting sections and include all but the last rpc and possibly non-rpc
            display_frames, file,line,method,code = self._collect_frames(False, i, file,line,method,code)
            assert len(display_frames)>0
            have_required_sections = True
            rpc_frames, file,line,method,code = self._collect_frames(True, i, file,line,method,code)

            # should have raised StopIteration if did not find at least some displayable frames
            while True:
                # each time we find another section of non-endpoing followed by endpoint,
                # include the prior two in the display but save these two potential skipped sections
                more_non_rpc, file,line,method,code = self._collect_frames(False, i, file,line,method,code)
                display_frames += rpc_frames + more_non_rpc
                more_rpc, file,line,method,code = self._collect_frames(True, i, file,line,method,code)
                rpc_frames = more_rpc
        except StopIteration:
            finished_iterating = True
            pass
        except Exception,e:
            print 'WARNING: RPCStackFormatter failed to filter frames in stack %r' % stack

        # if we did not find enough sections in the right order, use the whole stack
        return display_frames if have_required_sections and finished_iterating else stack

    def _collect_frames(self, is_endpoint, i, file,line,method,code):
        # iterate and check if lines are ignored endpoints,
        # if there is at least one line beyond this section, return list and next frame;
        # if this section extends to the end of iterations, raise StopIteration
        frames = []
        while self._is_endpoint(file)==is_endpoint:
            frames.append((file,line,method,code))
            file,line,method,code = i.next()
        return frames,file,line,method,code

    def _is_endpoint(self, file):
        return file.endswith('pyon/net/endpoint.py') or file.endswith('pyon/ion/endpoint.py')

def change_logging_level(logger,level):
    '''
    Change the logging level for a given logger or for all loggers by using 'all'

    Example:
      from pyon.util.log import CRITICAL,DEBUG, change_logging_level
      change_logging_level('all', CRITICAL)
      change_logging_level('pyon', DEBUG)

    WARNING: MAGIC VALUE ANTIPATTERN: prevents use of a logger called "all".
    TODO: make more obscure:  None?  __all__
    '''

    assert level in logging._levelNames

    if logger=='all':
        config.set_all_levels(level)
    else:
        config.set_level(logger,level)
