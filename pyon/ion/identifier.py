#!/usr/bin/env python

"""Functions for ION identifiers"""

__author__ = 'Michael Meisinger'

import uuid

RES_PREFIX = "ion$res"
ASSOC_PREFIX = "ion$asc"
DIR_PREFIX = "ion$dir"
EVENT_PREFIX = "ion$evt"


def create_unique_identifier(prefix):
    return uuid.uuid4().hex


def create_unique_resource_id():
    return create_unique_identifier(RES_PREFIX)


def create_unique_association_id():
    return create_unique_identifier(ASSOC_PREFIX)


def create_unique_directory_id():
    return create_unique_identifier(DIR_PREFIX)


def create_unique_event_id():
    return create_unique_identifier(EVENT_PREFIX)


def create_simple_unique_id():
    return uuid.uuid4().hex


def is_ion_id(identifier):
    return identifier.startswith("ion$")


def is_resource_id(identifier):
    return identifier.startswith(RES_PREFIX)


def is_directory_id(identifier):
    return identifier.startswith(DIR_PREFIX)


def is_event_id(identifier):
    return identifier.startswith(EVENT_PREFIX)
