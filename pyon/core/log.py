"""Basic pyon logging (with or without container)

   NOTE: the functionality of this module has moved to ooi.logging.config.
         currently this module is maintained for API compatability, but is implemented using the new package.
"""

import logging
from ooi.logging import config

DEFAULT_LOGGING_PATHS = ['res/config/logging.yml', 'res/config/logging.local.yml']
logging_was_configured = False

def configure_logging(logging_conf_paths, logging_config_override=None):
    """
    Public call to configure and initialize logging.
    @param logging_conf_paths  List of paths to logging config YML files (in read order)
    @param config_override  Dict with config entries overriding files read
    """
    global logging_was_configured
    logging_was_configured = True

    for path in logging_conf_paths:
        try:
            config.add_configuration(path)
        except Exception, e:
            print 'WARNING: could not load logging configuration file %s: %s' % (path, e)
    if logging_config_override:
        try:
            config.add_configuration(logging_config_override)
        except Exception,e:
            print 'WARNING: failed to apply logging override %r: %e' % (logging_config_override,e)
            
    # direct warnings mechanism to loggers
    logging.captureWarnings(True)


def is_logging_configured():
    """ allow caller to determine if logging has already been configured in this container """
    global logging_was_configured
    return logging_was_configured or config.get_configuration()
