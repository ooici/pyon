#!/usr/bin/env python

"""Basic pyon logging (with or without container) """

__author__ = 'Michael Meisinger, Thomas Lennan'

# @WARN: GLOBAL STATE

import os

# -------------------------------------------------
# Pyon logging initialization

# Keeps the logging configuration dict
LOGGING_CFG = None

def _read_logging_config(logging_conf_paths):
    from pyon.util.config import Config
    global LOGGING_CFG
    LOGGING_CFG = Config(logging_conf_paths, ignore_not_found=True).data

def _override_config(config_override):
    if type(config_override) is not dict:
        print "pyon: WARNING: config_override is not dict but", config_override
    from pyon.util.containers import dict_merge
    dict_merge(LOGGING_CFG, config_override)

def _initialize_logging():
    # Create directories as configured for all logging handlers
    for handler in LOGGING_CFG.get('handlers', {}).itervalues():
        if 'filename' in handler:
            log_dir = os.path.dirname(handler['filename'])
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

    # if there's no logging config, we can't configure it: the call requires version at a minimum
    if LOGGING_CFG:
        import logging.config
        logging.config.dictConfig(LOGGING_CFG)


def configure_logging(logging_conf_paths, logging_config_override=None):
    """
    Public call to configure and initialize logging.
    @param logging_conf_paths  List of paths to logging config YML files (in read order)
    @param config_override  Dict with config entries overriding files read
    """
    _read_logging_config(logging_conf_paths)
    if logging_config_override:
        _override_config(logging_config_override)
    _initialize_logging()
