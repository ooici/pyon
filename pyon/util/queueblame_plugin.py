from nose.plugins import Plugin
from collections import defaultdict

class QueueBlame(Plugin):
    name = 'queueblame'

    def __init__(self):
        Plugin.__init__(self)
        import uuid
        self.ds_name = "queueblame-%s" % str(uuid.uuid4())[0:6]

        self.queues_by_test = defaultdict(lambda: defaultdict(dict))

    def options(self, parser, env):
        super(QueueBlame, self).options(parser, env=env)

        parser.add_option('--queueblame-purge', action='store_true', dest='queueblame_purge', help='Purge queues with leftover messages and remove all bindings')

    def configure(self, options, conf):
        """Configure the plugin and system, based on selected options."""
        super(QueueBlame, self).configure(options, conf)

        self._queueblame_purge      = options.queueblame_purge

    def begin(self):
        self._active_queues = set()
        self._test_changes = {}
        self._queues_declared = []          # ordered list of queues declared
        self._queues = defaultdict(list)    # queue name -> list of accesses

        # Make sure we initialize pyon before anything in this plugin executes
        from pyon.core import bootstrap
        if not bootstrap.pyon_initialized:
            bootstrap.bootstrap_pyon()

        from pyon.ion.exchange import ExchangeManager
        from pyon.util.containers import DotDict
        from pyon.core.bootstrap import CFG
        from mock import Mock

        containermock = Mock()
        containermock.resource_registry.find_resources.return_value = ([], None)

        self.ex_manager = ExchangeManager(containermock)      # needs to be able to setattr
        self.ex_manager._nodes['priviledged'] = DotDict(client=DotDict(parameters=DotDict(host=CFG.get_safe('server.amqp.host', 'localhost'))))

    def finalize(self, result):
        pass

    def beforeTest(self, test):
        self._pre_defs = self.ex_manager.get_definitions()

        import os
        os.environ['QUEUE_BLAME'] = str(test.id())

    def afterTest(self, test):
        import os
        from pyon.core.bootstrap import get_sys_name        # can't guarantee exclusive access

        #os.environ.pop('QUEUE_BLAME')
        tid = test.id()

        post_defs = self.ex_manager.get_definitions()

        # diff the defs
        pre_queues = {str(x['name']) for x in self._pre_defs['queues']}
        post_queues = {str(x['name']) for x in post_defs['queues']}

        pre_exchanges = {str(x['name']) for x in self._pre_defs['exchanges']}
        post_exchanges = {str(x['name']) for x in post_defs['exchanges']}

        pre_binds = { (x['source'], x['destination'], x['routing_key']) for x in self._pre_defs['bindings'] if x['destination_type'] == 'queue' }
        post_binds = { (x['source'], x['destination'], x['routing_key']) for x in post_defs['bindings'] if x['destination_type'] == 'queue' }

        queue_diff_add      = post_queues.difference(pre_queues)
        exchange_diff_add   = post_exchanges.difference(pre_exchanges)
        binds_diff_add      = post_binds.difference(pre_binds)

        queue_diff_sub      = pre_queues.difference(post_queues)
        exchange_diff_sub   = pre_exchanges.difference(post_exchanges)
        binds_diff_sub      = pre_binds.difference(post_binds)

        # maintain active queue set
        map(self._active_queues.add, queue_diff_add)
        map(self._active_queues.discard, queue_diff_sub)

        # maintain changelog for tests
        self._test_changes[tid] = (queue_diff_add, queue_diff_sub, exchange_diff_add, exchange_diff_sub, binds_diff_add, binds_diff_sub)

        # add any new leftover queues to the list
        for q in queue_diff_add:
            if not q in self._queues_declared:
                self._queues_declared.append(q)

        # get stats about each leftover queue and record the access

        raw_queues_list = self.ex_manager._list_queues()
        raw_queues = { str(x['name']) : x for x in raw_queues_list }

        for q in self._queues_declared:

            # detect if queue has been deleted (and not readded)
            if len(self._queues[q]) > 0 and isinstance(self._queues[q][-1], str) and not q in queue_diff_add:
                continue

            # did we just delete it this test? add the sentinel
            if q in queue_diff_sub:
                self._queues[q].append(tid)
                continue

            # record the test, # messages on it, + bindings on the queue, - bindings on the queue
            self._queues[q].append( (tid,
                                     str(raw_queues[q]['messages']),
                                     [x for x in binds_diff_add if str(x[1]) == str(q)],
                                     [x for x in binds_diff_sub if str(x[1]) == str(q)]))

            # are we supposed to purge it / kill bindings?
            if self._queueblame_purge and raw_queues[q]['messages'] > 0:

                # remove bindings via API
                binds = self.ex_manager.list_bindings_for_queue(q)
                for bind in binds:
                    self.ex_manager.delete_binding_tuple(bind)

                    # add to list of removed bindings for report
                    rem_binds = self._queues[q][-1][3]
                    rem_binds.append(tuple(bind[0:2] + (bind[2] + " (PURGED)",)))

                # purge
                self.ex_manager.purge_queue(q)

    def report(self, stream):
        table = []
        for q in self._queues_declared:

            qd = self._queues[q]

            # first rows are:
            # queue     + test          # messages
            #             +B exchange   binding
            table.append([q, "+", qd[0][0], qd[0][1]])

            for bind in qd[0][2]:
                table.append(["", "", "    +B ex: %s key: %s" % (bind[0], bind[2]), ""])

            # add rest of accesses
            #             test          # messages
            #             +B exchange   binding
            #             -B exchange   binding
            for qdd in qd[1:]:
                if isinstance(qdd, str):
                    table.append(["", "-", qdd, ""])
                else:
                    table.append(["", "", qdd[0], qdd[1]])

                    for bind in qdd[2]:
                        table.append(["", "", "    +B ex: %s key: %s" % (bind[0], bind[2]), ""])
                    for bind in qdd[3]:
                        table.append(["", "", "    -B ex: %s key: %s" % (bind[0], bind[2]), ""])

        # header
        table.insert(0, ['Queue', '', 'Test', '# Msg'])

        # get widths
        widths = [max([len(row[x]) for row in table]) for x in xrange(len(table[0]))]
        fmt_out = [" ".join([x.ljust(widths[i]) for i, x in enumerate(row)]) for row in table]

        # insert col separation row
        fmt_out.insert(1, " ".join([''.ljust(widths[i], '=') for i in xrange(len(widths))]))

        # write this all to sstream
        stream.write("Queue blame report (purge: %s)\n" % (self._queueblame_purge))

        stream.write("\n".join(fmt_out))
        stream.write("\n")

