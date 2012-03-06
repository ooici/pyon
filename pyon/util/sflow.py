#!/usr/bin/env python

"""sFlow integration for pyon"""
from random import random

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.util.async import spawn
import time
import json
from socket import socket, AF_INET, SOCK_DGRAM
import os

class SFlowManager(object):

    def __init__(self, container):
        self._container         = container
        self._gl_counter        = None
        self._counter_interval  = 20            # @TODO: default: from cfg
        self._hsflowd_addr      = "localhost"   # @TODO same
        self._hsflowd_port      = 7777          # @TODO same
        self._hsflowd_conf      = "/etc/hsflowd.auto"
        self._conf_last_mod     = None          # last modified time of the conf file
        self._trans_sample_rate = 1

    def start(self):
        log.debug("SFlowManager.start")
        self._gl_counter = spawn(self._counter)

        self._udp_socket = socket(AF_INET, SOCK_DGRAM)

    def stop(self):
        log.debug("SFlowManager.stop")
        self._gl_counter.kill()

    def _counter(self):
        """
        Publish counter stats on a periodic basis.

        Should be spawned in a greenlet via start.
        """
        while True:
            # ensure counter interval is up to date
#            self._read_interval_time()

            log.debug("SFlowManager._counter: sleeping for %s", self._counter_interval)

            time.sleep(self._counter_interval)

            # build and send counter structure
            csample = { 'counters_sample': {
                            'app_name': str(self._container.id),
                            'app_resources': {
                                'user_time': 0,
                                'system_time': 0,
                                'mem_used': 0,
                                'mem_max': 0,
                                'fd_open': 0,
                                'fd_max': 0,
                                'conn_open': 0,
                                'conn_max': 0
                            }
                        },
                        'app_workers':{
                            'workers_active': len(self._container.proc_manager.proc_sup.children),
                            'workers_idle': 0,
                            'workers_max': 1024,
                            'req_delayed': 0,
                            'req_dropped': 0
                        }
                      }

            log.debug("Publishing counter stats: %s" % csample)

            self._publish(csample)

    def _read_interval_time(self):
        """
        Reads the hsflowd conf file to determine what time should be used.
        """
        try:
            mtime = os.stat(self._hsflowd_conf).st_mtime
        except OSError:
            log.info("Could not stat hsflowd.auto file")
            mtime = self._conf_last_mod

        if mtime != self._conf_last_mod:
            self._conf_last_mod = mtime

            # appears to be simple key=value, one per line
            try:
                with open(self._hsflowd_conf) as f:
                    while True:
                        c = f.readline()
                        if c == "":
                            break
                        elif c.startswith('polling='):
                            self._counter_interval = int(c.rstrip().split('=')[1])
                            log.debug("New polling interval time: %d", self._counter_interval)
                            break
            except IOError:
                log.exception("Could not open/read hsflowd.auto")

    def transaction(self, op=None,
                          attrs=None,
                          status_descr=None,
                          status=None,
                          req_bytes=None,
                          resp_bytes=None,
                          uS=None,
                          initiator=None,
                          target=None):
        """
        Record a transaction (typically completed RPC).

        Called from Process level endpoint layer.
        """
        sampling_probability = 1.0 / self._trans_sample_rate
        log.debug("Transaction (sampling prob: %f)", sampling_probability)
        if random() <= sampling_probability:
            log.debug("Sampling")
            tsample = { 'flow_sample':{
                            'app_name': str(self._container.id),
                            'sampling_rate': 1,     # @TODO ??
                            'app_operation': {
                                'operation': op,
                                'attributes': "&".join(["%s=%s" % (k, v) for k, v in attrs.iteritems()]),
                                'status_descr': status_descr,
                                'status': status,
                                'req_bytes': req_bytes,
                                'resp_bytes': resp_bytes,
                                'uS': uS
                            },
                            'app_initiator': {
                                'actor': initiator,
                            },
                            'app_target': {
                                'actor': target,
                            }
                        }
                      }

            self._publish(tsample)
        else:
            log.debug("Not sampling this transaction")

    def _publish(self, data):
        """
        Converts args to JSON and publishes via UDP to configured host/port.
        """
        json_data = json.dumps(data)
        self._udp_socket.sendto(json_data, (self._hsflowd_addr, self._hsflowd_port))

