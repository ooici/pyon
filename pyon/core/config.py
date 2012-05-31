'''
Created on May 29, 2012

@author: tomlennan
'''

import inspect

#from pyon.util.log import log

def load_config():
    from pyon.container.cc import Container
    from pyon.core.bootstrap import IonObject, CFG
    from pyon.core.exception import Conflict
    from pyon.util.containers import dict_merge

    # Conditionally load from directory
    config_from_directory = CFG.get_safe("system.config_from_directory", False)
    if config_from_directory:
        de = Container.instance.directory.lookup("/Config/CFG")
        if not de:
            raise Conflict("Expected /Config/CFG in directory. Correct Org??")
        dict_merge(CFG, de, inplace=True)

    # Look for and apply any local file config overrides
    from pyon.util.config import Config
    conf_paths = ['res/config/pyon.local.yml']

    local_cfg = Config(conf_paths, ignore_not_found=True).data
    dict_merge(CFG, local_cfg, inplace=True)

def bootstrap_object_defs():
    from pyon.container.cc import Container
    from pyon.core.object import IonObjectBase
    from interface import objects

    delist = []
    for cname, cobj in inspect.getmembers(objects, inspect.isclass):
        if issubclass(cobj, IonObjectBase) and cobj != IonObjectBase:
            parentlist = [parent.__name__ for parent in cobj.__mro__ if parent.__name__ not in ['IonObjectBase','object']]
            delist.append(("/ObjectTypes", cname, dict(schema=cobj._schema, extends=parentlist)))
    Container.instance.directory.register_mult(delist)

def bootstrap_service_defs():
    from pyon.container.cc import Container
    from pyon.core.bootstrap import service_registry

    svc_list = []
    for svcname, svc in service_registry.services.iteritems():
        svc_list.append(("/ServiceInterfaces", svcname, {}))
    Container.instance.directory.register_mult(svc_list)

def bootstrap_config():
    from pyon.container.cc import Container
    from pyon.core.bootstrap import CFG

    auto_bootstrap = CFG.get_safe("system.auto_bootstrap", False)
    if auto_bootstrap:
        Container.instance.directory.register("/Config", "CFG", **CFG.copy())

        # TODO relocate?
        bootstrap_object_defs()
        bootstrap_service_defs()

