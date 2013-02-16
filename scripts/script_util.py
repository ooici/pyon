#!/usr/bin/env python
import yaml

"""Utilities for working with Pyon independent scripts"""

__author__ = 'Adam R. Smith, Michael Meisinger'

import collections
from copy import deepcopy
import yaml

def parse_args(tokens):
    """
    Parses extra args from Python's argparse.
    Exploit yaml's spectacular type inference (and ensure consistency with config files)
    """
    args, kwargs = [], {}
    for token in tokens:
        token = token.lstrip('-')
        if '=' in token:
            key,val = token.split('=', 1)
            ipython_cfg = unflatten({key: yaml.load(val)})
            dict_merge(kwargs, ipython_cfg, inplace=True)
            #kwargs.update(ipython_cfg)
        else:
            args.append(yaml.load(token))

    return args, kwargs

def unflatten(dictionary):
    # From http://stackoverflow.com/questions/6037503/python-unflatten-dict/6037657#6037657
    resultDict = dict()
    for key, value in dictionary.iteritems():
        parts = key.split(".")
        d = resultDict
        for part in parts[:-1]:
            if part not in d:
                d[part] = dict()
            d = d[part]
        d[parts[-1]] = value
    return resultDict

# Exact copy of pyon.util.containers.
# @TODO Could not find a common place to import from. Remove redundancy in the long run

def quacks_like_dict(object):
    """Check if object is dict-like"""
    return isinstance(object, collections.Mapping)

def dict_merge(base, upd, inplace=False):
    """Merge two deep dicts non-destructively.
    Uses a stack to avoid maximum recursion depth exceptions.
    @param base the dict to merge into
    @param upd the content to merge
    @param inplace change base if True, otherwise deepcopy base
    @retval the merged dict (base if inplace else a merged deepcopy)
    """
    assert quacks_like_dict(base), quacks_like_dict(upd)
    dst = base if inplace else deepcopy(base)

    stack = [(dst, upd)]
    while stack:
        current_dst, current_src = stack.pop()
        for key in current_src:
            if key not in current_dst:
                current_dst[key] = current_src[key]
            else:
                if quacks_like_dict(current_src[key]) and quacks_like_dict(current_dst[key]) :
                    stack.append((current_dst[key], current_src[key]))
                else:
                    current_dst[key] = current_src[key]
    return dst
