#!/usr/bin/env python

"""Helper functions for working with interfaces"""

__author__ = 'Seman Said, Michael Meisinger'

from pyon.ion.resregistry_standalone import ResourceRegistryStandalone
from yaml import load as yaml_load
from yaml.constructor import ConstructorError


def get_object_definition_from_datastore(sysname):
    fragments = []

    rr = ResourceRegistryStandalone(sysname=sysname)
    obj_types = rr.find_by_type('ObjectType')
    if not obj_types:
        return ''
    for item in obj_types:
        try:
            fragments.append((item['definition_order'], item['definition']))
        except:
            return ''
    fragments = [item for ordinal, item in sorted(fragments)]
    full_definition = "\n".join(fragments)
    return full_definition


def get_service_definition_from_datastore(sysname):
    fragments = []
    rr = ResourceRegistryStandalone(sysname=sysname)
    svc_defs = rr.find_by_type('ServiceDefinition')
    if not svc_defs:
        return ''
    for item in svc_defs:
        try:
            fragments.append(item['definition'])
        except:
            return ''
    full_definition = "\n".join(fragments)
    return full_definition


def is_yaml_string_valid(yaml_string):
    try:
        yaml_load(yaml_string)
    except ConstructorError:
        return True
    except:
        return False
    return True
