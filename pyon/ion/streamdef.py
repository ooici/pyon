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

    def __eq__(self, sd2):
        return str(self) == str(sd2)

    def __ne__(self, sd2):
        return not self == sd2

    def __repr__(self):
        retval = str(self)
        if len(retval) >= 14:
            retval = retval[:14] + '...'
        return '<%s "%s" at 0x%x>' % (self.__class__.__name__, retval, id(self))

    def __str__(self):
        return etree.tostring(self._element)

    def __contains__(self, xpath):
        return bool(self.xpath(xpath))
