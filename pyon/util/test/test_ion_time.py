#!/usr/bin/env python
'''
@author: Luke Campbell <LCampbell@ASAScience.com>
@file pyon/util/test/test_ion_time.py
@date Fri Jul 20 10:26:55 EDT 2012
@description Utilities for dealing with NTP time stamps
'''

from pyon.util.unit_test import PyonTestCase
from pyon.util.ion_time import IonTime
from nose.plugins.attrib import attr
import time
import numpy as np
import datetime

@attr('UNIT')
class IonTimeUnitTest(PyonTestCase):
    def test_time_ntp_fidelity(self):
        it1 = IonTime()
        ntp_ts = it1.to_ntp64()
        it2 = IonTime.from_ntp64(ntp_ts)
        self.assertEquals(it1.seconds,it2.seconds)
        self.assertTrue(np.abs(it1.useconds - it2.useconds) <= 1)

    def test_time_string_fidelity(self):
        it1 = IonTime()
        ntp_str = it1.to_string()
        it2 = IonTime.from_string(ntp_str)
        
        self.assertEquals(it1.seconds,it2.seconds)
        self.assertTrue(np.abs(it1.useconds - it2.useconds) <= 1)


    def test_unix_time_fidelity(self):
        ts = time.time()
        it1 = IonTime(ts)

        ts_2 = it1.to_unix()
        self.assertTrue(np.abs(ts - ts_2) <= 1e-3)

    def test_ntp_compatability(self):
        unix_day = IonTime(datetime.datetime(1970,1,1))
        self.assertEquals(unix_day.era , 0)
        self.assertEquals(unix_day.seconds , 2208988800)

        utc_day = IonTime(datetime.datetime(1972,1,1))
        self.assertEquals(utc_day.era , 0)
        self.assertEquals(utc_day.seconds , 2272060800)

        millen_day = IonTime(datetime.datetime(2000,1,1))
        self.assertEquals(millen_day.era , 0)
        self.assertEquals(millen_day.seconds , 3155673600)

        ntp_era1 = IonTime(datetime.datetime(2036,2,8))
        self.assertEquals(ntp_era1.era , 1)
        self.assertEquals(ntp_era1.seconds , 63104)
        self.assertEquals(ntp_era1.to_unix() , 2086041600.)


