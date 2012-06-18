#!/usr/bin/env python

"""Pyon configuration and config file loading utilities"""

__author__ = 'Thomas Lennan, Michael Meisinger'

# @WARN: GLOBAL STATE, STATIC CODE

import inspect

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

def read_standard_configuration():
    pyon_cfg = read_local_configuration(pyon.DEFAULT_CONFIG_PATHS)
    apply_local_configuration(pyon_cfg, pyon.DEFAULT_LOCAL_CONFIG_PATHS)
    return pyon_cfg

def apply_remote_config(system_cfg):
    from pyon.core.bootstrap import get_sys_name
    from pyon.core.exception import Conflict
    from pyon.ion.directory_standalone import DirectoryStandalone
    directory = DirectoryStandalone(sysname=get_sys_name(), config=system_cfg)

    de = directory.lookup("/Config/CFG")
    if not de:
        raise Conflict("Expected /Config/CFG in directory. Correct Org??")
    apply_configuration(system_cfg, de)

# -------------------------------------------------
# ION system auto bootstrapping

def recursive_strip(scan_obj):
    """
    HACK HACK HACK
    """
    if type(scan_obj) is dict:
        for key, value in scan_obj.iteritems():
            if type(value) not in (str, int, float, bool, dict, list, None):
                scan_obj[key] = str(value)
            if type(value) is dict:
                recursive_strip(value)

def _bootstrap_object_defs(directory):
    from pyon.core.object import IonObjectBase
    from interface import objects

    # @TODO: This should use the same code as the load_configuration tool
    delist = []
    for cname, cobj in inspect.getmembers(objects, inspect.isclass):
        if issubclass(cobj, IonObjectBase) and cobj != IonObjectBase:
            parentlist = [parent.__name__ for parent in cobj.__mro__ if parent.__name__ not in ['IonObjectBase','object']]
            delist.append(("/ObjectTypes", cname, dict(schema=recursive_strip(cobj._schema), extends=parentlist)))
    directory.register_mult(delist)

def _bootstrap_service_defs(directory):
    from pyon.service.service import IonServiceRegistry

    # @TODO: This should use the same code as the load_configuration tool
    # At this time importing everything is THE KILLER
    service_registry = IonServiceRegistry()
    service_registry.load_service_mods('interface/services')
    service_registry.build_service_map()

    svc_list = []
    for svcname, svc in service_registry.services.iteritems():
        svc_list.append(("/ServiceInterfaces", svcname, {}))
    directory.register_mult(svc_list)

def auto_bootstrap_datastores(bootstrap_config):
    from pyon.core.bootstrap import get_sys_name
    from pyon.datastore.couchdb.couchdb_standalone import CouchDataStore
    ds = CouchDataStore(config=bootstrap_config)
    datastores = ['resources','directory']
    for dsn in datastores:
        qual_ds_name = ("%s_%s" % (get_sys_name(), dsn)).lower()
        if not ds.exists_datastore(qual_ds_name):
            ds.create_datastore(qual_ds_name)
            # NOTE: Views are created by containers' DatastoreManager

def auto_bootstrap_config(bootstrap_config, system_cfg):
    print "pyon: config: Auto bootstrap CFG into directory"
    from pyon.core.bootstrap import get_sys_name
    from pyon.ion.directory_standalone import DirectoryStandalone
    directory = DirectoryStandalone(sysname=get_sys_name(), config=bootstrap_config)
    de = directory.lookup("/Config/CFG")
    if not de:
        directory.register("/Config", "CFG", **system_cfg.copy())

def auto_bootstrap_interfaces(bootstrap_config):
    print "pyon: config: Auto bootstrap interfaces into directory"
    from pyon.core.bootstrap import get_sys_name
    from pyon.ion.directory_standalone import DirectoryStandalone
    directory = DirectoryStandalone(sysname=get_sys_name(), config=bootstrap_config)
    de = directory.lookup("/ServiceInterfaces")
    if not de:
        # TODO: Check this and use proper imports here
        _bootstrap_object_defs(directory)
        _bootstrap_service_defs(directory)
