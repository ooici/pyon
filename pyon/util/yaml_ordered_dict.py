#!/usr/bin/env python

"""
Force pyyaml to use OrderedDict by default.
Recipe found at: http://pyyaml.org/attachment/ticket/161/use_ordered_dict.py
"""

import yaml
import collections


def construct_ordered_mapping(self, node, deep=False):
    if not isinstance(node, yaml.MappingNode):
        raise ConstructorError(None, None,
                "expected a mapping node, but found %s" % node.id,
                node.start_mark)
    mapping = collections.OrderedDict()
    for key_node, value_node in node.value:
        key = self.construct_object(key_node, deep=deep)
        if not isinstance(key, collections.Hashable):
            raise ConstructorError("while constructing a mapping", node.start_mark,
                    "found unhashable key", key_node.start_mark)
        value = self.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping

def construct_yaml_map_with_ordered_dict(self, node):
    data = collections.OrderedDict()
    yield data
    value = self.construct_mapping(node)
    data.update(value)

def represent_ordered_mapping(self, tag, mapping, flow_style=None):
    value = []
    node = yaml.MappingNode(tag, value, flow_style=flow_style)
    if self.alias_key is not None:
        self.represented_objects[self.alias_key] = node
    best_style = True
    if hasattr(mapping, 'items'):
        mapping = list(mapping.items())
    for item_key, item_value in mapping:
        node_key = self.represent_data(item_key)
        node_value = self.represent_data(item_value)
        if not (isinstance(node_key, yaml.ScalarNode) and not node_key.style):
            best_style = False
        if not (isinstance(node_value, yaml.ScalarNode) and not node_value.style):
            best_style = False
        value.append((node_key, node_value))
    if flow_style is None:
        if self.default_flow_style is not None:
            node.flow_style = self.default_flow_style
        else:
            node.flow_style = best_style
    return node


def apply_yaml_patch():
    """
    This function applies a monkey patch to the current YAML library, so that
    it returns OrderedDict instead of dict
    """
    #if yaml.constructor.BaseConstructor.construct_mapping == construct_ordered_mapping:
    #    return

    yaml.constructor.BaseConstructor.construct_mapping = construct_ordered_mapping

    yaml.constructor.Constructor.add_constructor(
        'tag:yaml.org,2002:map',
        construct_yaml_map_with_ordered_dict)

    yaml.representer.BaseRepresenter.represent_mapping = represent_ordered_mapping

    yaml.representer.Representer.add_representer(collections.OrderedDict,
        yaml.representer.SafeRepresenter.represent_dict)

