#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@file pyon/ion/streamdef.py
@date Thu Jul  5 14:40:49 EDT 2012
@description Utility for managing stream definitions
'''

from lxml import etree


class StreamDef(object):
    def __init__(self, xml_string):
        self._element = etree.fromstring(xml_string)

    def xpath(self, path):
        return self._element.xpath(path)


