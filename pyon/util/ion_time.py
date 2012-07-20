#!/usr/bin/env python
'''
@author: Luke Campbell <LCampbell@ASAScience.com>
@file pyon/util/ion_time.py
@date Fri Jul 20 10:26:55 EDT 2012
@description Utilities for dealing with NTP time stamps
'''
import numpy as np
import time

class IonTime(object):
    '''
    Utility wrapper for handling time in ntpv4
    '''
    FRAC = np.float32(4294967296.)
    JAN_1970 = np.uint32(2208988800)

    def __init__(self,date=None): 
        '''Can be initialized with a standard unix time stamp'''
        if date is None:
            date = time.time()
        self.seconds = np.uint32(date + self.JAN_1970)
        self.useconds = np.uint32((date - int(date)) * 1e6)

    def __repr__(self):
        return '<%s "%s" at 0x%x>' % (self.__class__.__name__, str(self), id(self))

    def __str__(self):
        ts = self.seconds + (self.useconds/1e6)
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts))

    def to_ntp(self):
        '''
        Converts the IonTime object into a RFC 5905 (NTPv4) compliant 64bit time stamp
        '''
        left = np.uint64(self.seconds << 32)
        right = np.uint64(self.useconds / 1e6 * self.FRAC)
        timestamp = np.uint64(left + right)
        return self.htonll(timestamp)
        
    def from_ntp(self, val):
        '''
        Converts a RFC 5905 (NTPv4) compliant 64bit time stamp into an IonTime object
        '''
        val = self.htonll(val)
        left = np.uint64(val) >> np.uint64(32)
        right = (np.uint64(val) & np.uint64(4294967295)) * 1e6 / self.FRAC
        self.seconds = np.uint32(left)
        self.useconds = np.uint32(right)

    def to_string(self):
        '''
        Creates a hexidecimal string of the NTP time stamp (serialization)
        '''
        val = self.to_ntp().tostring()
        arr = [0] * 8
        for i in xrange(8):
            arr[i] = '%02x' % ord(val[i])
        return ''.join(arr)

    def from_string(self, s):
        '''
        Changes this IonTime object to reflect the stringified time stamp
        '''
        s = self.htonstr(s)
        ntp_ts = np.uint64(int(s,16))
        self.from_ntp(ntp_ts)

    def to_unix(self):
        '''
        Returns the unix time stamp for this IonTime
        '''
        return float(self.seconds - self.JAN_1970 + (self.useconds/1e6))

    @staticmethod
    def htonstr(val):
        import sys
        if sys.byteorder == 'little':
            l = len(val)
            nval = [0] * l
            for i in xrange(l/2):
                nval[i*2]  = val[l - i*2 - 2]
                nval[i*2+1]= val[l - i*2 - 1]
            return ''.join(nval)
        return val



    @staticmethod
    def htonl(val):
        import sys
        val = np.uint32(val)
        if sys.byteorder == 'little':
            return val.byteswap()
        return val

    @staticmethod
    def htonll(val):
        import sys
        val = np.uint64(val)
        if sys.byteorder == 'little':
            return val.byteswap()
        return val


