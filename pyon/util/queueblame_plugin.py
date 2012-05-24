from nose.plugins import Plugin

class QueueBlame(Plugin):
    name = 'queueblame'

    def __init__(self):
        Plugin.__init__(self)
        from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
        import uuid
        self.ds_name = "queueblame-%s" % str(uuid.uuid4())[0:6]
        self.ds = CouchDB_DataStore(datastore_name=self.ds_name)

        from collections import defaultdict
        self.queues_by_test = defaultdict(lambda: defaultdict(dict))

    def options(self, parser, env):
        super(QueueBlame, self).options(parser, env=env)

        parser.add_option('--queueblame-by-queue', action='store_true', dest='queueblame_by_queue', help='Show output by queue instead of by test', default=False)
        parser.add_option('--queueblame-full', action='store_true', dest='queueblame_full', help='Display ALL queues, not just queues with consumers/msgs')
        parser.add_option('--queueblame-no-trim', action='store_false', dest='queueblame_trim', help='Trim output so that repeated test names/queue names are omitted for brevity. Human readable but not easily machine readable.', default=True)

    def configure(self, options, conf):
        """Configure the plugin and system, based on selected options."""
        super(QueueBlame, self).configure(options, conf)

        self._queueblame_by_queue   = options.queueblame_by_queue
        self._queueblame_full       = options.queueblame_full
        self._queueblame_trim       = options.queueblame_trim

    def begin(self):
        self.ds.create_datastore(create_indexes=False)


    def finalize(self, result):
        self.ds.delete_datastore()
        self.ds.close()

    def beforeTest(self, test):
        import os
        os.environ['QUEUE_BLAME'] = "%s,%s" % (self.ds_name, test.id())

    def afterTest(self, test):
        from pyon.net.transport import NameTrio, TransportError
        from pyon.net.channel import RecvChannel
        import os
        import sys

        # need a connection to node to get queue stats
        from pyon.net.messaging import make_node
        node, ioloop = make_node()

        os.environ.pop('QUEUE_BLAME')
        tid = test.id()

        # grab raw data from database
        obj_ids = self.ds.list_objects()
        objs = self.ds.read_doc_mult(obj_ids)

        for x in objs:
            queue = x['queue_name']

            if 'accesses' in self.queues_by_test[tid][queue]:
                self.queues_by_test[tid][queue]['accesses'] += 1
            else:
                # grab intel from channel
                ch = node.channel(RecvChannel)
                ch._recv_name = NameTrio(queue.split('.')[0], queue)

                try:
                    msgs, consumers = ch.get_stats()
                    exists = True
                    #print >>sys.stderr, "LOG ME", queue, msgs, consumers
                except TransportError:
                    msgs = 0
                    consumers = 0
                    exists = False
                finally:
                    ch.close()

                self.queues_by_test[tid][queue] = { 'exists': exists,
                                                    'msgs': msgs,
                                                    'consumers' : consumers,
                                                    'accesses' : 1 }

        # must also check all the queues from previous tests, to capture bleed
        bleed_queues = set()
        for test, testqueues in self.queues_by_test.iteritems():
            if test != tid:
                map(bleed_queues.add, testqueues.iterkeys())

        # don't test anything we already just tested
        bleed_queues.difference_update(self.queues_by_test[tid].iterkeys())

        for queue in bleed_queues:
            ch = node.channel(RecvChannel)
            ch._recv_name = NameTrio(queue.split('.')[0], queue)

            try:
                msgs, consumers = ch.get_stats()
                exists = True
            except TransportError:
                msgs = 0
                consumers = 0
                exists = False

            # drain the queue!
            if exists and msgs > 0 and consumers == 0:
                print >>sys.stderr, "DRAIN QUEUE:", queue
                ch.start_consume()
                for x in xrange(msgs):
                    m, h, d = ch.recv()
                    print >>sys.stderr, h
                    ch.ack(d)

            ch.close()


            self.queues_by_test[tid][queue] = { 'exists': exists,
                                                'msgs': msgs,
                                                'consumers': consumers,
                                                'accesses' : 0 }        # 0 is special here, indicates a bleed check

        # empty the database for next test use
        self.ds.delete_datastore()
        self.ds.create_datastore(create_indexes=False)

        node.stop_node()
        ioloop.join(timeout=5)

    def report(self, stream):

        # format report
        table = []
        self.total_count = 0

        def is_interesting(qd):
            """
            Helper method, returns if a row is interesting based on msgs, consumers and queueblame_full flag.
            """
            return self._queueblame_full or (not self._queueblame_full and (qd['msgs'] > 0 or qd['consumers'] > 0))

        def add_row(first, second, queuedict):
            """
            Can be called with queue/test or test/queue first, hence generic name.

            Returns bool indicated row was added or not.
            """
            self.total_count += 1
            if is_interesting(queuedict):
                acc = ' '
                if queuedict['accesses'] > 1:
                    acc = queuedict['accesses']
                elif queuedict['accesses'] == 0:
                    acc = 'PREV'
                exists = 'T' if queuedict['exists'] else 'F'
                table.append([str(x) for x in [first, second, acc, exists, queuedict['msgs'], queuedict['consumers']]])

                return True

            return False

        # create tests by queue, used in a few places below
        from collections import defaultdict
        tests_by_queue = defaultdict(list)

        for test, queues in self.queues_by_test.iteritems():
            for queue, queuedict in queues.iteritems():
                tests_by_queue[queue].append(dict(queuedict, test=test))

        # list of queues that are tagged as PREV, we keep tabs on it but only use it later if correct conditions
        prev_list = set()

        # build output table
        if not self._queueblame_by_queue:
            for test, queues in self.queues_by_test.iteritems():
                for queue, queuedict in queues.iteritems():
                    ret = add_row(test, queue, queuedict)
                    if ret and queuedict['accesses'] == 0:
                        prev_list.add(queue)
        else:
            for queue, calls in tests_by_queue.iteritems():
                for call in calls:
                    ret = add_row(queue, call['test'], call)
                    if ret and queuedict['accesses'] == 0:
                        prev_list.add(queue)


        # generate prev_list table if it is interesting
        prev_list_table = []
        if not self._queueblame_full:
            for prev in prev_list:
                # cut down dict
                prev_accesses = [qd['test'] for qd in tests_by_queue[prev] if qd['accesses'] > 0]

                for pa in prev_accesses:
                    prev_list_table.append([prev, pa])

        # sort by first col
        table.sort(cmp=lambda x,y: cmp(x[0], y[0]))
        prev_list_table.sort(cmp=lambda x,y: cmp(x[0], y[0]))

        # do we trim?
        if self._queueblame_trim:
            last = ""
            for i, x in enumerate(table):
                if x[0] != last:
                    last = x[0]
                else:
                    table[i][0] = ""
            last = ""
            for i, x in enumerate(prev_list_table):
                if x[0] != last:
                    last = x[0]
                else:
                    prev_list_table[i][0] = ""

        if self._queueblame_by_queue:
            table.insert(0, ['Queue', 'Test', '# Acc >1', 'Ex?', '# Msgs', '# Cnsmrs'])
        else:
            table.insert(0, ['Test', 'Queue', '# Acc >1', 'Ex?', '# Msgs', '# Cnsmrs'])

        if len(prev_list_table) > 0:
            prev_list_table.insert(0, ['Queue', 'Test'])
            # format prev_table too
            widths = [max([len(row[x]) for row in prev_list_table]) for x in xrange(len(prev_list_table[0]))]
            prev_fmt_out = [" ".join([x.ljust(widths[i]) for i, x in enumerate(row)]) for row in prev_list_table]
            prev_fmt_out.insert(1, " ".join([''.ljust(widths[i], '=') for i in xrange(len(widths))]))
        else:
            prev_fmt_out = []

        # calculate widths
        widths = [max([len(row[x]) for row in table]) for x in xrange(len(table[0]))]
        fmt_out = [" ".join([x.ljust(widths[i]) for i, x in enumerate(row)]) for row in table]
        # insert col separation row
        fmt_out.insert(1, " ".join([''.ljust(widths[i], '=') for i in xrange(len(widths))]))

        stream.write("\n" + "=" * len(fmt_out[0]) + "\n\n")
        stream.write("Queue blame report (DB: %s, full: %s, by_queue: %s)\n" % (self.ds_name, self._queueblame_full, self._queueblame_by_queue))
        stream.write("If 'PREV' in accesses column, indicates queue was not accessed during this test and could indicate bleed between tests.\n")
        if not self._queueblame_full and len(table) > 1:
            stream.write("\n*** The following queues still have messages or consumers! ***\n")
        stream.write("\n")
        stream.write("\n".join(fmt_out))
        stream.write("\n" + "=" * len(fmt_out[0]) + "\n")
        stream.write("%d shown of %d total\n" % (len(table)-1, self.total_count))
        stream.write("\n")
        if len(prev_fmt_out) > 0:
            stream.write("\n\nThe following queues were accessed by the associated tests, inspect them for proper cleanup of subscribers!\n\n")
            stream.write("\n".join(prev_fmt_out))
            stream.write("\n" + "=" * len(prev_fmt_out[0]) + "\n")
            stream.write("\n")

