#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@file pyon/ion/streamdef.py
@date Thu Jul  5 14:40:49 EDT 2012
@description Utility for managing stream definitions
'''

from pyon.util.unit_test import PyonTestCase
from pyon.ion.streamdef import StreamDef
from nose.plugins.attrib import attr

xml_def1 = '''
<stream-definition>
  <conductivity />
  <temperature />
  <depth />
</stream-definition>'''
xml_def2 = '''
<stream-definition>
  <temperature />
</stream-definition>'''





@attr('UNIT')
class StreamDefUnitTest(PyonTestCase):
    def test_stream_def_compare(self):
        stream_def1 = StreamDef(xml_def1)
        stream_def2 = StreamDef(xml_def2)

        stream_def3 = StreamDef(xml_def1)

        self.assertTrue(stream_def1 == stream_def3)
        self.assertFalse(stream_def1 == stream_def2)
        self.assertTrue(stream_def1 != stream_def2)

        self.assertTrue('/stream-definition/temperature' in stream_def1)
        self.assertTrue('/stream-definition/temperature' in stream_def2)
        self.assertTrue('/stream-definition/conductivity' in stream_def1)
        self.assertFalse('/stream-definition/conductivity' in stream_def2)


