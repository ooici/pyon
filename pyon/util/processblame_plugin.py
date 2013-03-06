from nose.plugins import Plugin

class ProcessLeak(Plugin):
    """
    Plugin to detect runaway processes in tests on the server side. It is intended to work against a live process
    dispatcher service during the entire nose run.  Therefore, it works in conjunction with --with-pycc plugin
    or a light CEI or full launch.  Use greenleak plugin instead for leak detection in non-pycc mode.
    """
    name = "processleak"

    def __init__(self):
        Plugin.__init__(self)

    def options(self, parser, env):
        super(ProcessLeak, self).options(parser, env=env)

        parser.add_option("--list-procs", action="store_true", dest="list_procs", \
                help="List all new procs created during the test")
    def configure(self, options, conf):
        super(ProcessLeak, self).configure(options, conf)

        self._list_procs = options.list_procs

    def begin(self):
        from interface.services.cei.iprocess_dispatcher_service import ProcessDispatcherServiceClient
        from pyon.net.messaging import make_node
        from pyon.core import bootstrap
        from pyon.public import CFG

        self.base_pids = []
        self.rpc_timeout = 2
        self._procs_by_test = {}
        if not bootstrap.pyon_initialized:
            bootstrap.bootstrap_pyon()
        self.node, self.ioloop = make_node()
        self.node.setup_interceptors(CFG.interceptor)
        self.pd_cli =  ProcessDispatcherServiceClient(node=self.node)

    def beforeTest(self, test):
        from pyon.core.exception import Timeout
        try:
           self.base_pids = [ proc.process_id for proc in self.pd_cli.list_processes(timeout=self.rpc_timeout) ]
        except Timeout:
           pass

    def afterTest(self, test):
        from pyon.core.exception import Timeout
        from interface.objects import ProcessStateEnum
        try:
            current = self.pd_cli.list_processes(timeout=self.rpc_timeout)
            from interface.objects import ProcessStateEnum
            procs_leaked = [ (proc.process_id, ProcessStateEnum._str_map.get(proc.process_state)) for proc in current \
                if proc.process_id not in self.base_pids and proc.process_state \
                not in [ProcessStateEnum.TERMINATED, ProcessStateEnum.EXITED] ]
            if self._list_procs:
                all_procs = [ (proc.process_id, ProcessStateEnum._str_map.get(proc.process_state)) for proc in current \
                if proc.process_id not in self.base_pids ]
            if len(procs_leaked) > 0:
                [ self.pd_cli.cancel_process(proc[0], timeout=self.rpc_timeout) for proc in procs_leaked ]
                if self._list_procs:
                    self._procs_by_test[test.id()] = all_procs
                else:
                    self._procs_by_test[test.id()] = procs_leaked
        except Timeout:
            pass

    def report(self, stream):
        table = []

        for tid, procs in self._procs_by_test.iteritems():

            # printable tid: don't need the full path
            ptid = ".".join(tid.split(".")[-2:])

            table.append([ptid, ""])
            for proc in procs:
                table.append(["", str(proc)])

            table.append(["", ""])

        # header
        table.insert(0, ['Test', 'Leaked Processes'])

        # get widths
        widths = [max([len(row[x]) for row in table]) for x in xrange(len(table[0]))]
        fmt_out = [" ".join([x.ljust(widths[i]) for i, x in enumerate(row)]) for row in table]

        # insert col separation row
        fmt_out.insert(1, " ".join([''.ljust(widths[i], '=') for i in xrange(len(widths))]))

        # write this all to sstream
        stream.write("Process leak report\n")

        stream.write("\n".join(fmt_out))
        stream.write("\n")

    def finalize(self, result):
        self.node.stop_node()
        self.ioloop.join()
