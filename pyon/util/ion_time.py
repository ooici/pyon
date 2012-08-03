#!/usr/bin/env python
'''
@author: Luke Campbell <LCampbell@ASAScience.com>
@file pyon/util/ion_time.py
@date Fri Jul 20 10:26:55 EDT 2012
@description Utilities for dealing with NTP time stamps
'''
import numpy as np
import time
import datetime
import struct
import numbers

class IonDate(datetime.date):
    def __new__(cls,*args):
        if len(args) == 3:
            return datetime.date.__new__(cls,*args)
        elif len(args) == 1:
            if isinstance(args[0],basestring):
                dt = datetime.datetime.strptime(args[0], '%Y-%m-%d')
                return datetime.date.__new__(cls, dt.year, dt.month, dt.day)
            elif isinstance(args[0], datetime.date):
                dt = args[0]
                return datetime.date.__new__(cls,dt.year, dt.month, dt.day)
        raise TypeError('Required arguments are (int,int,int) or (str) in the "YYYY-MM-DD" pattern')

class IonTime(object):
    '''
    Utility wrapper for handling time in ntpv4
    Everything is in ZULU Time
    '''
    FRAC = np.float32(4294967296.)
    JAN_1970 = np.uint32(2208988800)
    EPOCH = datetime.datetime(1900,1,1)

    ntpv4_timestamp = '! 2I'
    ntpv4_date      = '! 2I Q'

    def __init__(self,date=None): 
        '''Can be initialized with a standard unix time stamp'''
        if date is None:
            date = time.time()
        if isinstance(date,numbers.Number):
            self._dt = datetime.datetime.utcfromtimestamp(date)
        elif isinstance(date,datetime.datetime):
            self._dt = date
        elif isinstance(date,datetime.date):
            self._dt = datetime.datetime.combine(date,datetime.time())

    @property
    def year(self):
        return self._dt.year
    @property
    def month(self):
        return self._dt.month
    @property
    def day(self):
        return self._dt.day
    @property
    def hour(self):
        return self._dt.hour
    @property
    def minute(self):
        return self._dt.minute
    @property
    def second(self):
        return self._dt.second
    @property
    def date(self):
        return IonDate(self.year, self.month, self.day)


    @property
    def era(self):
        delta = (self._dt - self.EPOCH).total_seconds()
        return np.uint32( int(delta) / 2**32)

    @property
    def seconds(self):
        delta = self._dt - self.EPOCH
        return np.uint32(np.trunc(delta.total_seconds()))

    @seconds.setter
    def seconds(self,value):
        delta = datetime.timedelta(seconds=value)
        self._dt = self.EPOCH + delta

    @property
    def useconds(self):
        delta = self._dt - self.EPOCH
        return np.uint32(np.modf(delta.total_seconds())[0] * 1e6)

    def __repr__(self):
        return '<%s "%s" at 0x%x>' % (self.__class__.__name__, str(self), id(self))

    def __str__(self):
        return self._dt.isoformat()

    def to_ntp64(self):
        '''
        Returns the NTPv4 64bit timestamp
           0                   1                   2                   3
           0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
          |                            Seconds                            |
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
          |                            Fraction                           |
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        
        '''
        delta = (self._dt - self.EPOCH).total_seconds()
        seconds = np.uint32(np.trunc(delta))
        fraction = np.uint32((delta - int(delta)) * 2**32)
        timestamp = struct.pack(self.ntpv4_timestamp, seconds, fraction)
        return timestamp
    
    @classmethod
    def from_ntp64(cls, val):
        '''
        Converts a RFC 5905 (NTPv4) compliant 64bit time stamp into an IonTime object
        '''
        seconds, fraction = struct.unpack(cls.ntpv4_timestamp, val)
        it = cls()
        it.seconds = seconds + (fraction *1e0 / 2**32)
        return it


    def to_ntp_date(self):
        '''
        Returns the NTPv4 128bit date timestamp
           0                   1                   2                   3
           0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
          |                           Era Number                          |
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
          |                           Era Offset                          |
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
          |                                                               |
          |                           Fraction                            |
          |                                                               |
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        '''
        delta = (self._dt - self.EPOCH).total_seconds()
        era = int(delta) / (2**32)
        offset = np.uint32(np.trunc(delta)) # Overflow does all the work for us
        fraction = np.uint64((delta - int(delta)) * 2**64)
        ntp_date = struct.pack(self.ntpv4_date, era,offset,fraction)
        return ntp_date

    @classmethod
    def from_ntp_date(cls, value):
        '''
        Returns an IonTime object based on the 128bit RFC 5905 (NTPv4) Date Format
        '''
        era, seconds, fraction = struct.unpack(cls.ntpv4_date, value)
        it = cls()
        it.seconds = (era * 2**32) + seconds + (fraction * 1e0 / 2**64)
        return it

    def to_string(self):
        '''
        Creates a hexidecimal string of the NTP time stamp (serialization)
        '''
        val = self.to_ntp64()
        assert len(val) == 8
        arr = [0] * 8
        for i in xrange(8):
            arr[i] = '%02x' % ord(val[i])
        retval = ''.join(arr)
        return retval

    def to_extended_string(self):
        '''
        Creates a hexidecimal string of the NTP date format (serialization)
        '''
        val = self.to_ntp_date()
        assert len(val) == 16
        arr = [0] * 16
        for i in xrange(16):
            arr[i] = '%02x' % ord(val[i])
        retval = ''.join(arr)
        return retval

    
    @classmethod
    def from_string(cls, s):
        '''
        Creates an IonTime object from the serialized time stamp
        '''
        assert len(s) == 16
        arr = [0] * 8
        for i in xrange(8):
            arr[i] = chr(int(s[2*i:2*i+2],16))
        retval = ''.join(arr)
        it = cls.from_ntp64(retval)
        return it
    
    @classmethod
    def from_extended_string(cls, s):
        '''
        Creates an IonTime object from the serialized extended time stamp
        '''
        assert len(s) == 32
        arr = [0] * 16 
        for i in xrange(16):
            arr[i] = chr(int(s[2*i:2*i+2],16))
        retval = ''.join(arr)
        it = cls.from_ntp_date(retval)
        return it

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


