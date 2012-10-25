#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@date Thu Oct 25 15:41:44 EDT 2012
@file pyon/util/poller.py
@brief Utility for polling
'''

import gevent

def poll(poller, *args, **kwargs):
    '''
    Polls a callback (poller) until success is met
    poller must be a valid callback and returns True on success
    '''
    timeout = 10
    if 'timeout' in kwargs:
        timeout = kwargs['timeout']
        kwargs.pop('timeout')
    success = False
    with gevent.timeout.Timeout(timeout):
        while not success:
            success = poller(*args, **kwargs)
            gevent.sleep(0.2)
    return success


