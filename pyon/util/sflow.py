#!/usr/bin/env python

"""sFlow integration for pyon"""

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.util.async import spawn
from pyon.core.bootstrap import CFG, get_sys_name
import time
import json
from socket import socket, AF_INET, SOCK_DGRAM
import os
from random import random
import resource

class SFlowManager(object):
    """
    An SFlow emit point.

    This manager exists inside the Container and speaks JSON over UDP to an hsflowd process.
    It is responsible for two types of samples:
    - Counter Samples: periodic samples giving system/user CPU time for this process, and memory info
    - Transaction Samples: logical "operations" in the code, such as a completed RPC request

    To use SFlow in your container, put the following lines in your pyon.local.yml:

    container:
      sflow:
        enabled: True
        hsflowd_addr: localhost                 # wherever hsflowd is running
        hsflowd_port: 36343
        hsflowd_auto_file: /etc/hsflowd.auto    # if hsflowd is not localhost, this doesn't matter
        trans_sample_rate: 1                    # 1 == transaction sample everything!

    """

    # map our status (http-based) to a status sFlow understands - as appropriate
    # http://sflow.org/draft_sflow_application.txt
    status_map = {200:    0,      # SUCCESS
                  400:    4,      # BAD_REQUEST
                  401:    10,     # UNAUTHORIZED
                  404:    8,      # NOT_FOUND
                  -1:     2,      # TIMEOUT
                  503:    9}

    def __init__(self, container):
        self._container         = container
        self._gl_counter        = None
        self._conf_last_mod     = None          # last modified time of the conf file

        sflowcfg                = CFG.get_safe('container.sflow', {})
        self._counter_interval  = CFG.get_safe('container.sflow.counter_interval', 30)          # number of seconds between counter pulses, 0 means don't do it
        self._hsflowd_addr      = CFG.get_safe("container.sflow.hsflowd_addr", "localhost")     # host where hsflowd is running
        self._hsflowd_port      = CFG.get_safe("container.sflow.hsflowd_port", 36343)           # udp port on host where hsflowd is listening for json
        self._hsflowd_conf      = CFG.get_safe("container.sflow.hsflowd_auto_file", "/etc/hsflowd.auto")    # hsflowd auto-conf file, where we poll for updates (only if addr is local)
        self._trans_sample_rate = CFG.get_safe("container.sflow.trans_sample_rate", 1)          # transaction sample rate, 1 means do everything!

    def start(self):
        log.debug("SFlowManager.start")

        if self._counter_interval > 0:
            self._gl_counter = spawn(self._counter)
        else:
            log.debug("Counter interval is 0, not spawning counter greenlet")

        self._udp_socket = socket(AF_INET, SOCK_DGRAM)

    def stop(self):
        log.debug("SFlowManager.stop")
        if self._gl_counter:
            self._gl_counter.kill()

    def _counter(self):
        """
        Publish counter stats on a periodic basis.

        Should be spawned in a greenlet via start.
        """
        while True:
            # ensure counter interval is up to date
            self._read_interval_time()

            log.debug("SFlowManager._counter: sleeping for %s", self._counter_interval)

            time.sleep(self._counter_interval)

            # get a cpu times sample
            res = resource.getrusage(resource.RUSAGE_SELF)

            # build and send counter structure
            csample = { 'counters_sample': {
                            'app_name': str(self._container.id),
                            'app_resources': {
                                'user_time': int(res.ru_utime * 1000),
                                'system_time': int(res.ru_stime * 1000),
                                'mem_used': 0,   # @TODO
                                'mem_max': res.ru_maxrss * 1024,
                                'fd_open': 0,   # @TODO do we care?
                                'fd_max': 0,    # @TODO ""
                                'conn_open': 0, # @TODO couch/rabbit connection summary somehow
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
        if not (self._hsflowd_addr == "localhost" or self._hsflowd_addr == "127.0.0.1"):
            log.debug("Skipping reading hsflow auto file, hsflowd is not running locally")
        else:
            try:
                mtime = os.stat(self._hsflowd_conf).st_mtime
            except OSError:
                # if you can't stat it, you can't read it most likely
                log.info("Could not stat hsflowd.auto file")
                return

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

    @property
    def should_sample(self):
        """
        Use this before building your transaction sample/calling transaction, as we may be configured
        to sample randomly.

        if sflow_manager.should_sample:
            # build params
            sflow_manager.transaction(app_name=name, op=...)
        """
        sampling_probability = 1.0 / self._trans_sample_rate
        log.debug("should_sample (sampling prob: %f)", sampling_probability)

        return random() <= sampling_probability

    def transaction(self, app_name=None,
                          op=None,
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

        log.debug("SFlowManager.transaction")

        # build up the true app name
        full_app = ['ion', get_sys_name()]

        # don't duplicate the container (proc ids are typically containerid.number)
        if self._container.id in app_name:
            full_app.append(app_name)
        else:
            full_app.extend((self._container.id, app_name))

        full_app_name = ".".join(full_app)

        tsample = { 'flow_sample':{
                        'app_name': full_app_name,
                        'sampling_rate': self._trans_sample_rate,
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

    def _publish(self, data):
        """
        Converts args to JSON and publishes via UDP to configured host/port.
        """
        json_data = json.dumps(data)
        self._udp_socket.sendto(json_data, (self._hsflowd_addr, self._hsflowd_port))
