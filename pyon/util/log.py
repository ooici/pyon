#!/usr/bin/env python
import cStringIO
import traceback
from pyon.core.exception import IonException

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import __builtin__
import logging
import sys
import socket
from logging.handlers import SysLogHandler, SYSLOG_UDP_PORT


DEBUG     = 'DEBUG'
INFO      = 'INFO'
WARNING   = 'WARNING'
ERROR     = 'ERROR'
CRITICAL  = 'CRITICAL'
EXCEPTION = 'EXCEPTION'



class StackFormatter(logging.Formatter):
    def __init__(self,*a,**b):
        super(StackFormatter,self).__init__(*a,**b)
        self._format_args = {'formatter': self._format_rpc_stack}
        self._filter_frames = True
        self.set_filename_width(40)

    def set_filename_width(self, width):
        self._filename_width = width
        self._format_string = '%%%ds:%%-7d%%s'%width

    def set_stack_formatter(self, formatter):
        if filter is None:                      # use default in exception.py
            del self._format_args['formatter']
        elif filter == 'RPC':                   # skip RPC framework
            self._format_args['formatter']=self._format_rpc_stack
        else:
            self._format_args['formatter']=formatter  # use caller-defined format

    def formatException(self, record):
        type,ex,tb = sys.exc_info()
        # use special exception logging only for IonExceptions with more than one saved stack
        if isinstance(ex,IonException) and len(ex.get_stacks())>1:
            return ex.format_stack(**self._format_args)
        else:
            super(StackFormatter,self).formatException(record)

    def _format_rpc_stack(self, label, stack):
        top_stack = label=='__init__'  # skip initial label -- start output with first stack frame
        if not top_stack:
            yield '   ----- '+label+' -----'

        frames = self._get_frames(top_stack, stack) if self._filter_frames else stack

        # create format string to align frames evenly, limit filename to 40chars
        w=self._filename_width
        p=-w
        s=self._format_string
        for file,line,method,code in frames:
            file_part = file if len(file)<w else file[p:]
            yield s%(file_part,line,code)

    def _get_frames(self, top_stack, stack):
        # split stack into these sections:
        # [non-endpoint], endpoint, displayable, endpoint, [non-endpoint]
        #
        # TODO: first and last sections should be [non-endpoint,non-project],
        #       can drop greenlet, pika, etc; but make sure we don't drop too much
        have_required_sections = False
        display_frames = None
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
            pass

        # if we did not find enough sections in the right order, use the whole stack
        return display_frames if have_required_sections else stack

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

class StackLogger(logging.Logger):
    def __init__(self, *a, **b):
        super(StackLogger,self).__init__(*a, **b)
        self.stack_formatter = StackFormatter()
        handler = logging.StreamHandler()
        handler.setFormatter(self.stack_formatter)
        self.addHandler(handler)
    def set_stack_formatter(self, formatter):
        self.stack_formatter.set_stack_formatter(formatter)

class Pyon_SysLogHandler(logging.handlers.SysLogHandler):
    """
    Class to override built-in syslog handler to work around
    issue where log records that are over MTU get dropped.
    We will chunk the message up so it at least gets logged.
    """ 
    MTU = 1400

    def __init__(self, address=('localhost', SYSLOG_UDP_PORT),
                 facility=SysLogHandler.LOG_USER, socktype=socket.SOCK_DGRAM, MTU=1400):
        SysLogHandler.__init__(self, address, facility, socktype)
        self.MTU = MTU
        
    def emit(self, record):
        message = record.getMessage()
        msg_len = len(message)
        if msg_len > self.MTU:
            # Chunk message into MTU size parts
            start_index = 0
            end_index = self.MTU - 1
            while True:
                msg = message[start_index:end_index]
                rec = logging.LogRecord(record.name, record.levelno, record.pathname, record.lineno, msg, None, record.exc_info, record.funcName)
                SysLogHandler.emit(self, rec)
                start_index = start_index + self.MTU
                if start_index >= msg_len:
                    break
                end_index = end_index + self.MTU
                if end_index > msg_len:
                    end_index = msg_len - 1
        else:
            SysLogHandler.emit(self, record)

# List of module names that will pass-through for the magic import scoping. This can be modified.
import_paths = [__name__]

def get_logger(loggername=__name__):
    """
    Creates an instance of a logger.
    Adds any registered handlers with this factory.

    Note: as this method is called typically on module load, if you haven't
    registered a handler at this time, that instance of a logger will not
    have that handler.
    """
    logger = logging.getLogger(loggername)

    return logger

# Special placeholder object, to be swapped out for each module that imports this one
log = None

def get_scoped_log(framestoskip=1):
    frame = sys._getframe(framestoskip)
    name = frame.f_locals.get('__name__', None)

    while name in import_paths and frame.f_back:
        frame = frame.f_back
        name = frame.f_locals.get('__name__', None)

#    logging.setLoggerClass(StackLogger)
    log = get_logger(name) if name else None
    return log

_orig___import__ = __import__
def _import(name, globals=None, locals=None, fromlist=None, level=-1):
    """
    Magic import mechanism  to get a logger that's auto-scoped to the importing module. Example:
    from pyon.public import scoped_log as log

    Inspects the stack; should be harmless since this is just syntactic sugar for module declarations.
    """
    kwargs = dict()
    if globals:
        kwargs['globals'] = globals
    if locals:
        kwargs['locals'] = locals
    if fromlist:
        kwargs['fromlist'] = fromlist
    kwargs['level'] = level
    module = _orig___import__(name, **kwargs)
    if name in import_paths and ('log' in fromlist or '*' in fromlist):
        log = get_scoped_log(2)
        setattr(module, 'log', log)

    return module
__builtin__.__import__ = _import

# Workaround a quirk in python 2.7 with custom imports
from logging.config import BaseConfigurator
BaseConfigurator.importer = staticmethod(_import)

log = get_scoped_log()

def change_logging_level(level):
    assert level in [DEBUG, INFO, WARNING, ERROR, CRITICAL]
    from pyon.core.log import LOGGING_CFG
    import logging.config
    for k,v in LOGGING_CFG['loggers'].iteritems():
        LOGGING_CFG['loggers'][k]['level'] = level
    logging.config.dictConfig(LOGGING_CFG)
