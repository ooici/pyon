#!/usr/bin/env python
import yaml

"""Utilities for working with Pyon independent scripts"""

__author__ = 'Adam R. Smith, Michael Meisinger'


def parse_args(tokens):
    """
    Parses extra args fron Python's argparse.
    Exploit yaml's spectacular type inference (and ensure consistency with config files)
    """
    args, kwargs = [], {}
    for token in tokens:
        token = token.lstrip('-')
        if '=' in token:
            key,val = token.split('=', 1)
            ipython_cfg = unflatten({key: yaml.load(val)})
            kwargs.update(ipython_cfg)
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
