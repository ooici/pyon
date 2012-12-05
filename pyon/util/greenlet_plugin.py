from nose.plugins import Plugin
import gc
from greenlet import greenlet
import traceback

class GreenletLeak(Plugin):
    """
    Plugin to detect runaway greenlets in tests.
    """
    name = "greenletleak"

    def __init__(self):
        Plugin.__init__(self)

    def options(self, parser, env):
        super(GreenletLeak, self).options(parser, env=env)

        parser.add_option("--greenlet-kill", action="store_true", dest="greenlet_kill", help="Send kill to all leaked greenlets (very dangerous)")

    def configure(self, options, conf):
        super(GreenletLeak, self).configure(options, conf)

        self._greenlet_kill = options.greenlet_kill

    def begin(self):
        self._gls_by_test = {}

    def _get_greenlets(self):
        """
        Gets a list of all greenlets the gc interface knows about.

        Adapted from http://blog.ziade.org/2012/05/25/zmq-and-gevent-debugging-nightmares/
        """
        return { obj for obj in gc.get_objects() if isinstance(obj, greenlet) and not obj.dead }

    def beforeTest(self, test):
        self._pre_gls = self._get_greenlets()

    def afterTest(self, test):
        post_gls = self._get_greenlets()

        gls_added = post_gls.difference(self._pre_gls)
        gls_deleted = self._pre_gls.difference(post_gls)

        if len(gls_added) > 0:
            self._gls_by_test[test.id()] = gls_added

    def report(self, stream):
        table = []

        for tid, gls in self._gls_by_test.iteritems():

            gls = list(gls)

            # printable tid: don't need the full path
            ptid = ".".join(tid.split(".")[-2:])

            table.append([ptid, str(gls[0])])

            def append_gl_status(gl):
                if gl.dead:
                    table.append(["", "    (dead)"])
                else:
                    # self of method greenlet is running (hopefully __repr__ is defined)
                    selfstr = "(none)"
                    if hasattr(gl._run.im_self):
                        selfstr = str(gl._run.im_self)
                    table.append(["", "self: " + selfstr])

                    # greenlet traceback (maybe interesting)
                    gltb = traceback.format_stack(gl.gr_frame)

                    for line in gltb:
                        for subline in line.split("\n")[0:2]:
                            table.append(["", "   " + subline])

            append_gl_status(gls[0])
            table.append(["", ""])

            for gl in gls[1:]:
                table.append(["", str(gl)])
                append_gl_status(gl)
                table.append(["", ""])

        # header
        table.insert(0, ['Test', 'Greenlet'])

        # get widths
        widths = [max([len(row[x]) for row in table]) for x in xrange(len(table[0]))]
        fmt_out = [" ".join([x.ljust(widths[i]) for i, x in enumerate(row)]) for row in table]

        # insert col separation row
        fmt_out.insert(1, " ".join([''.ljust(widths[i], '=') for i in xrange(len(widths))]))

        # write this all to sstream
        stream.write("Greenlet leak report\n")

        stream.write("\n".join(fmt_out))
        stream.write("\n")

