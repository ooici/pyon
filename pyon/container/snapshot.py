#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import os
import pprint
import socket
import sys

from ooi.timer import get_accumulators

from pyon.public import log, IonObject, BadRequest, CFG
from pyon.util.containers import get_ion_ts

DEFAULT_SNAPSHOTS = ["basic", "config", "processes", "policy", "accumulators", "gevent", "gevent_block"]


class ContainerSnapshot(object):
    def __init__(self, container):
        self.container = container
        self.snapshot = {}
        self.snap_ts = None
        self.snapshots = set(DEFAULT_SNAPSHOTS)

    def take_snapshot(self, snapshot_id=None, include_list=None, exclude_list=None, snapshot_kwargs=None):
        if include_list:
            self.snapshots.add(include_list)
        if exclude_list:
            for item in exclude_list:
                self.snapshots.remove(item)
        if not snapshot_id:
            snapshot_id = get_ion_ts()
        if not snapshot_kwargs:
            snapshot_kwargs = {}

        self.snapshot["snapshot_ts_begin"] = get_ion_ts()
        self.snapshot["snapshot_list"] = self.snapshots
        for snap in self.snapshots:
            snap_func = "_snap_%s" % snap
            func = getattr(self, snap_func, None)
            if func:
                try:
                    snap_result = func(**snapshot_kwargs)
                except Exception as ex:
                    log.warn("Could not take snapshot %s: %s" % (snap, str(ex)))
                self.snapshot[snap] = snap_result
            else:
                log.warn("Snapshot function %s undefined" % snap_func)

        self.snap_ts = get_ion_ts()
        self.snapshot["snapshot_ts"] = self.snap_ts
        self.snapshot["snapshot_id"] = snapshot_id

    def persist_snapshot(self):
        cc_id = self.container.proc_manager.cc_id
        cc_obj = self.container.resource_registry.read(cc_id)
        cc_obj.status_log.insert(0, self.snapshot)
        cc_obj.status_log = cc_obj.status_log[:3]
        self.container.resource_registry.update(cc_obj)
        return cc_id

    def log_snapshot(self):
        log.info("Container snapshot taken at %s" % self.snap_ts)
        log.info(pprint.pformat(self.snapshot))

    def clear_snapshots(self):
        cc_id = self.container.proc_manager.cc_id
        cc_obj = self.container.resource_registry.read(cc_id)
        cc_obj.status_log = []
        self.container.resource_registry.update(cc_obj)

    # -------------------------------------------------------------------------

    def _snap_basic(self, **kwargs):
        snap_result = {}
        snap_result["os.uname"] = os.uname()
        snap_result["os.getpid"] = os.getpid()
        snap_result["os.getppid"] = os.getppid()
        snap_result["socket.gethostname"] = socket.gethostname()
        snap_result["sys.argv"] = sys.argv
        snap_result["sys.version"] = sys.version
        snap_result["sys.subversion"] = sys.subversion

        try:
            import psutil
            proc = psutil.Process(os.getpid())

            snap_result["stat.vm.cpu_times"] = psutil.cpu_times()._asdict()
            snap_result["stat.vm.cpu_percent"] = str(psutil.cpu_percent())
            snap_result["stat.vm.virtual_memory"] = psutil.virtual_memory()._asdict()
            snap_result["stat.vm.swap_memory"] = psutil.swap_memory()._asdict()
            snap_result["stat.vm.disk_usage"] = psutil.disk_usage("/")._asdict()
            snap_result["stat.vm.disk_io_counters"] = psutil.disk_io_counters()._asdict()
            snap_result["stat.vm.disk_partitions"] = [o._asdict() for o in psutil.disk_partitions()]
            snap_result["stat.vm.net_io_counters"] = {k:v._asdict() for k,v in psutil.net_io_counters(pernic=True).iteritems()}

            snap_result["stat.proc.cpu_times"] = proc.get_cpu_times()._asdict()
            snap_result["stat.proc.cpu_percent"] = str(proc.get_cpu_percent())
            snap_result["stat.proc.mem_info"] = proc.get_ext_memory_info()._asdict()
            snap_result["stat.proc.create_time"] = str(proc.create_time)
            snap_result["stat.proc.mem_percent"] = str(proc.get_memory_percent())
            snap_result["stat.proc.open_files"] = [o._asdict() for o in proc.get_open_files()]
            #snap_result["stat.proc.connections"] = [o.__dict__ for o in proc.get_connections()]
            snap_result["stat.proc.ctx_switches"] = proc.get_num_ctx_switches()._asdict()
            #This might blow up if the machine doesn't have a real host name
            snap_result["socket.gethostbyname"] = socket.gethostbyname(socket.gethostname())
        except Exception as ex:
             log.warn("Could not take psutil stats: %s" % (str(ex)))

        return snap_result

    def _snap_config(self, **kwargs):
        snap_result = {}
        snap_result["os.environ"] = dict(os.environ)
        snap_result["CFG"] = CFG
        #snap_result["sys.modules"] = {n:str(m) for (n,m) in sys.modules.iteritems()}
        snap_result["sys.path"] = sys.path

        return snap_result

    def _snap_gevent(self, **kwargs):
        snap_result = {}

        greenlet_list = []
        snap_result["greenlets"] = greenlet_list

        # See http://stackoverflow.com/questions/12510648/in-gevent-how-can-i-dump-stack-traces-of-all-running-greenlets
        # See http://blog.ziade.org/2012/05/25/zmq-and-gevent-debugging-nightmares/
        # This may be an expensive operation
        # Working with stack traces has danger of memory leak, but it seems the code below is fine
        import gc
        import traceback
        from greenlet import greenlet
        greenlets = [obj for obj in gc.get_objects() if isinstance(obj, greenlet) and obj and not obj.dead]
        for ob in greenlets:
            greenlet_list.append((getattr(ob, "_glname", ""), ''.join(traceback.format_stack(ob.gr_frame))))
        return snap_result

    def _snap_gevent_block(self, **kwargs):
        from pyon.util.gevent_block_plugin import get_gevent_block
        snap_result = {}

        gevent_block_dict = {}
        snap_result["gevent_block"] = gevent_block_dict

        gevent_block = get_gevent_block()
        if gevent_block:
            #json encoding cannot take a non-string key. Let's clean it so it doesn't break persistence to db
            snap_shots = gevent_block.get_snapshots()
            for (_, gl_name), value in snap_shots.items():
                gevent_block_dict.update({gl_name:value})
        return snap_result

    def _snap_processes(self, **kwargs):
        proc_mgr = self.container.proc_manager
        snap_result = {}
        procs_dict = {}
        snap_result["procs"] = procs_dict
        for proc_id, proc in proc_mgr.procs.iteritems():
            procs_dict[proc_id] = dict(interface_name=proc.name,
                                       proc_name=proc._proc_name,
                                       proc_type=getattr(proc, "_proc_type", ""),
                                       proc_listen_name=getattr(proc, "_proc_listen_name", ""),
                                       proc_res_id=getattr(proc, "_proc_res_id", ""),
                                       proc_start_time=getattr(proc, "_proc_start_time", ""),
                                       proc_svc_id=getattr(proc, "_proc_svc_id", ""),
                                       resource_id=getattr(proc, "resource_id", ""),
                                       resource_type=getattr(proc, "resource_type", ""),
                                       time_stats=proc._process.time_stats
                                  )

        return snap_result

    def _snap_policy(self, **kwargs):
        gov_ctrl = self.container.governance_controller
        snap_result = gov_ctrl._get_policy_snapshot()
        snap_result["update_log"] = gov_ctrl._policy_update_log

        return snap_result

    def _snap_accumulators(self, **kwargs):
        all_acc_dict = {}
        for acc_name, acc in get_accumulators().iteritems():
            acc_dict = {}
            acc_name = acc_name.split(".")[-1]
            acc_name = acc_name[:30]
            all_acc_dict[acc_name] = acc_dict
            for key in acc.keys():
                count = acc.get_count(key)
                if count:
                    acc_dict[key] = dict(
                        _key=key,
                        count=count,
                        sum=str(acc.get_average(key) * count),
                        min=str(acc.get_min(key)),
                        avg=str(acc.get_average(key)),
                        max=str(acc.get_max(key)),
                        sdev=str(acc.get_standard_deviation(key))
                    )

        return all_acc_dict
