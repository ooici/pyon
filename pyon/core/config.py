#!/usr/bin/env python

"""Pyon configuration and config file loading utilities"""

__author__ = 'Thomas Lennan, Michael Meisinger'

import pyon


# -------------------------------------------------
# Pyon configuration load

def read_local_configuration(conf_paths):
    from pyon.util.config import Config
    pyon_cfg = Config(conf_paths, ignore_not_found=True).data
    return pyon_cfg


def apply_configuration(system_cfg, config_override):
    if not config_override:
        return
    from pyon.util.containers import dict_merge
    dict_merge(system_cfg, config_override, inplace=True)


def apply_local_configuration(system_cfg, local_conf_paths=None):
    if local_conf_paths:
        # Apply any local file config overrides
        local_cfg = read_local_configuration(local_conf_paths)
        apply_configuration(system_cfg, local_cfg)

def apply_profile_configuration(system_cfg, bootstrap_config):
    profile_filename = bootstrap_config.get_safe("container.profile", None)
    if not profile_filename:
        return
    if not profile_filename.endswith(".yml"):
        profile_filename = "res/profile/%s.yml" % profile_filename
    from pyon.util.config import Config
    profile_cfg = Config([profile_filename]).data
    config_override = profile_cfg.get_safe("profile.config")
    if config_override and isinstance(config_override, dict):
        from pyon.util.containers import dict_merge
        dict_merge(system_cfg, config_override, inplace=True)

def read_standard_configuration():
    pyon_cfg = read_local_configuration(pyon.DEFAULT_CONFIG_PATHS)
    apply_local_configuration(pyon_cfg, pyon.DEFAULT_LOCAL_CONFIG_PATHS)
    return pyon_cfg


def apply_remote_config(bootstrap_cfg, system_cfg):
    from pyon.core.bootstrap import get_sys_name
    from pyon.core.exception import Conflict
    from pyon.ion.directory_standalone import DirectoryStandalone
    directory = DirectoryStandalone(sysname=get_sys_name(), config=bootstrap_cfg)

    de = directory.lookup("/Config/CFG")
    if not de:
        raise Conflict("Expected /Config/CFG in directory. Correct Org??")
    apply_configuration(system_cfg, de)
