"""Basic pyon logging (with or without container)

   NOTE: the functionality of this module has moved to ooi.logging.config.
         currently this module is maintained for API compatability, but is implemented using the new package.
"""

from ooi.logging import config

def configure_logging(logging_conf_paths, logging_config_override=None):
    """
    Public call to configure and initialize logging.
    @param logging_conf_paths  List of paths to logging config YML files (in read order)
    @param config_override  Dict with config entries overriding files read
    """
    for path in logging_conf_paths:
        try:
            config.add_configuration(path)
        except IOError,e:
            print 'WARNING: did not find logging configuration file ' + path
    if logging_config_override:
        config.add_configuration(logging_config_override)
