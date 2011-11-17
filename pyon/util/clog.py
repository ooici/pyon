#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

# adapted from http://stackoverflow.com/questions/384076/how-can-i-make-the-python-logging-output-to-be-colored

import logging

class ColoredFormatter(logging.Formatter):
    """
    Colorized formatter.

    Specify your format string with $BOLD and $RESET (to end $BOLD, must be present).
    The log level and the message will be printed in a level-specific color. DEBUG level is
    not colorized.
    """
    DEFAULT_FMT = '[%(asctime)s %(levelname)-5s %(name)-10s:%(lineno)3d] %(message)s'
    #DEFAULT_FMT = "[$BOLD%(name)-20s$RESET][%(levelname)-18s]  %(message)s ($BOLD%(filename)s$RESET:%(lineno)d)"
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"

    COLORS = {
        'WARNING': MAGENTA,
        'INFO': WHITE,
        #'DEBUG': BLUE,     # debug is not interesting, don't color it
        'CRITICAL': GREEN,
        'ERROR': RED
    }

    def __init__(self, fmt=None, datefmt=None, use_color=True):
        fmt = fmt or self.DEFAULT_FMT
        logging.Formatter.__init__(self, self._replace_formatting(fmt, use_color), datefmt)
        self.use_color = use_color

    def format(self, record):
        if self.use_color and record.levelname in self.COLORS:
            levelname = record.levelname
            # background is set with 40 plus color, foreground with 30
            record.levelname    = self.COLOR_SEQ % (30 + self.COLORS[levelname]) + record.levelname + self.RESET_SEQ
            record.msg          = self.COLOR_SEQ % (30 + self.COLORS[levelname]) + record.msg + self.RESET_SEQ

        return logging.Formatter.format(self, record)

    def _replace_formatting(self, message, use_color=True):
        if use_color:
            message = message.replace("$RESET", self.RESET_SEQ).replace("$BOLD", self.BOLD_SEQ)
        else:
            message = message.replace("$RESET", "").replace("$BOLD", "")
        return message

class ColoredStreamHandler(logging.StreamHandler):
    """
    A colorized logging handler that can be specified in your logging.local.yml.

    Specify this class in your handler section like so:

    handlers:
      console:
        class: pyon.util.clog.ColoredStreamHandler
        formatter: yourformatter
        level: DEBUG
        stream: ext://sys.stdout

    formatters:
      yourformatter:
        format: '$BOLD%(asctime)s:$RESET %(message)s'
        datefmt: '%Y-%m-%d %H:%M:%S'
    """
    def setFormatter(self, fmt):
        logging.StreamHandler.setFormatter(self, ColoredFormatter(fmt._fmt, fmt.datefmt))