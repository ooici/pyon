""" create minimal-length, increasing IDs for couchdb """
from threading import Lock
from uuid import uuid4
from time import time
from random import choice


class IDFactory(object):
    def create_id(self):
        pass


class RandomIDFactory(IDFactory):
    def create_id(self):
        return uuid4().hex


class SaltedTimeIDFactory(IDFactory):
    """ generator for minimal-length, increasing ID values for couchdb

        ID is base64-encoded sequence of bits [ 42-bit time + random salt ]

        salt is saved and reused until a duplicate is reported.
        a duplicate can occur if two containers choose the same salt and perform an operation at the same (millisec) time.
        the likelyhood that no two systems out of N choose the same B-bit salt value is given by:
            [ (2^B - 1) / 2^B ] ^ [N * (N-1) / 2]
        with 14 bit salt values, this is 99% for 20 systems, 93% for 50 systems, 74% for 100 systems
        [ we only need to consider the number of systems providing RPC services -- not all nodes in the system ]

        if a duplicate occurs, the generator can change the salt and try again.  likelyhood of any one new salt matching
        another existing value for even large networks is extremely small.

        DB operations should get and attempt to save documents with the generated ID value, but be prepared to
        catch DB exceptions indicating duplicate ID, then replace and try again.
    """

    # chars are in ascii order to maintain ID sequence order
    _CHARSET = "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"

    def __init__(self, salt_chars=3):
        self._salt_chars = salt_chars
        self._change_salt()
        self._lock = Lock()
        self._last_time = 0

    def _change_salt(self):
        self._salt = [ choice(self._CHARSET) for n in xrange(self._salt_chars) ]

    def create_id(self):
#        buffer = bytearray((self._salt_bits + 42)/8)
        time_value = int(time() * 1000)  # 42bit millisecond value overflows ~ 2112

        # there is a slight chance that two IDs are reqeusted within a millisecond
        # if so, increment the time by one MS.
        self._lock.acquire()
        if time_value <= self._last_time:
            time_value = self._last_time + 1
        self._last_time = time_value
        self._lock.release()

        # explicit base64 encoding used b/c our charset differs and time doesn't fall on nice byte boundaries
        bits_used = 0
        id_chars = self._salt[:]
        while bits_used < 42:
            low_six_bits = time_value & 63
            id_chars[0:0] = self._CHARSET[low_six_bits]
            time_value /= 64
            bits_used += 6
        return ''.join(id_chars)

    def replace_duplicate(self):
        self._change_salt()
        return self.create_id()
