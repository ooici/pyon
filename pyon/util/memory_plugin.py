import resource
from resource import RUSAGE_SELF, RUSAGE_CHILDREN
import psutil

from nose.plugins.base import Plugin
import sys
debug = sys.stderr

class MemProfile(Plugin):
    """
    This plugin provides memory profiling in tests.

    """

    name = 'mem-profile'

    def options(self, parser, env):
        """Sets additional command line options."""
        super(MemProfile, self).options(parser, env)

    def configure(self, options, config):
        """Configures the test timer plugin."""
        super(MemProfile, self).configure(options, config)

    def begin(self):
        self._profiled_tests = []
        self.b_vm = None
        self.b_sru_maxrss = 0
        self.b_cru_maxrss = 0

    def startTest(self, test):
        self.b_vm = psutil.virtual_memory()
        self.b_sru_maxrss = resource.getrusage(RUSAGE_SELF).ru_maxrss
        self.b_cru_maxrss = resource.getrusage(RUSAGE_CHILDREN).ru_maxrss

        debug.write("Before: self maxrss=%s, children maxrss=%s, %s\n" % (self.b_sru_maxrss, self.b_cru_maxrss, str(self.b_vm)))

    def afterTest(self, test):
        a_vm = psutil.virtual_memory()
        a_sru_maxrss = resource.getrusage(RUSAGE_SELF).ru_maxrss
        a_cru_maxrss = resource.getrusage(RUSAGE_CHILDREN).ru_maxrss
        self._profiled_tests.append((test.id(), self.b_vm, self.b_sru_maxrss,
            self.b_cru_maxrss, a_vm, a_sru_maxrss, a_cru_maxrss))

        debug.write("After: self maxrss=%s, tchildren maxrss=%s, %s\n" % (a_sru_maxrss, a_cru_maxrss, str(a_vm)))

    def report(self, stream):
        table = []
        for test, b_vm, b_sru_maxrss, b_cru_maxrss, a_vm, a_sru_maxrss, a_cru_maxrss  \
                in self._profiled_tests:
            # printable tid: don't need the full path
            ptid = ".".join(test.split(".")[-2:])

            table.append([ptid, ""])
            table.append(["", "Before: self maxrss=%s, children maxrss=%s" % (b_sru_maxrss, b_cru_maxrss)])
            table.append(["", "%s" % str(b_vm)])
            table.append(["", "After : self maxrss=%s, children maxrss=%s" % (a_sru_maxrss, a_cru_maxrss)])
            table.append(["", "%s" % str(a_vm)])
            table.append(["", "Diff  : self maxrss=%s, children maxrss=%s" % (str(a_sru_maxrss - b_sru_maxrss),
                str(a_cru_maxrss - b_cru_maxrss))])
            table.append(["", ""])

            # header
            table.insert(0, ['Test', 'Memory Stats'])

            # get widths
            widths = [max([len(row[x]) for row in table]) for x in xrange(len(table[0]))]
            fmt_out = [" ".join([x.ljust(widths[i]) for i, x in enumerate(row)]) for row in table]

            # insert col separation row
            fmt_out.insert(1, " ".join([''.ljust(widths[i], '=') for i in xrange(len(widths))]))

            # write this all to sstream
            stream.write("Memory report\n")

            stream.write("\n".join(fmt_out))
            stream.write("\n")
