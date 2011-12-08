#!/usr/bin/env python

"""Provides the interactive API for the pyon container."""

__author__ = 'Michael Meisinger'

container = None

def get_console_dimensions():
    """Returns (rowns, columns) of current terminal"""
    import os
    rows, columns = os.popen('stty size', 'r').read().split()
    return int(rows), int(columns)

def get_max_width(table, index):
    """Get the maximum width of the given column index"""
    return max([len(str(row[index])) for row in table])

def pprint_table(table, pad=1, indent=0):
    """Prints out a table of data, padded for alignment
    @param out: Output stream (file-like object)
    @param table: The table to print. A list of lists.
    Each row must have the same number of columns.
    From:http://ginstrom.com/scribbles/2007/09/04/pretty-printing-a-table-in-python/
    """
    strl = []

    col_paddings = []
    for i in xrange(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        strl.append(' '*indent)
        for i in xrange(len(row)):
            col = str(row[i]).ljust(col_paddings[i] + pad)
            strl.append(col)
        strl.append('\n')

    return "".join(strl)

def pprint_list(l, c, pad=1, indent=0):
    """Pretty prints a list as table and returns string.
    @param l list to print
    @param c number of columns or -1 to optimize for console width
    @param pad whitespace padding between columns (1)
    @param indent whitespace indent
    """
    if c == -1:
        try:
            rows, columns = get_console_dimensions()

            table_n = None
            for c in xrange(1, min(columns/(pad+1), len(l))):
                table = table_n
                table_n = [l[c*i:c*i+c] for i in range(1+len(l)/c)]
                table_n[-1].extend(['']*(c-len(table_n[-1])))
                sumwid = indent
                for i in xrange(c):
                    sumwid += get_max_width(table_n, i)
                sumwid += pad * c
                if sumwid > columns:
                    if not table: table = table_n
                    break
        except Exception as ex:
            return pprint_list(l, 1, pad, indent)
    else:
        table = [l[c*i:c*i+c] for i in range(1+len(l)/c)]
        table_n[-1].extend(['']*(c-len(table_n[-1])))

    return pprint_table(table, pad, indent)


# -------------------------------------------------

def ps(ret=False):
    print "List of ION processes"
    print "---------------------"
    from pyon.service.service import services_by_name
    #print "\n".join(("%s: %s"%(sn, sd.__class__) for (sn,sd) in services_by_name.iteritems()))
    print "\n".join(("%s: %s"%(name, p) for (name,p) in container.proc_manager.procs.iteritems()))
    if ret:
        return container.proc_manager.procs

def procs(ret=False):
    print "\nList of pyon processes"
    print "----------------------"
    print "\n".join((str(p) for p in container.proc_manager.proc_sup.children))
    if ret:
        return container.proc_manager.proc_sup.children

def ms():
    print "List of messaging endpoints"
    print "---------------------------"
    #print "Servers (listeners):"
    from pyon.net.endpoint import EndpointFactory
    from collections import defaultdict
    endpoint_by_group = defaultdict(list)
    for elist in EndpointFactory.endpoint_by_name.values():
        for ep in elist:
            if hasattr(ep, "_process"):
                endpoint_by_group[ep._process.id].append(ep)
            else:
                endpoint_by_group["none"].append(ep)

    for name in sorted(endpoint_by_group.keys()):
        print "%s (%s)" % (name, container.proc_manager.procs[name]._proc_name if not name == "none" else "")
        print "\n".join(("  %s, %s"%(ed.name if hasattr(ed,'name') else '', ed) for ed in sorted(endpoint_by_group[name],
                                        key=lambda ep: (ep.__class__.__name__, getattr(ep, 'name')))))

def apps():
    print "List of active pyon apps"
    print "------------------------"
    print "\n".join(("%s: %s"%(appdef.name, appdef) for appdef in container.app_manager.apps))

def svc_defs(svcs=None, op=None):
    """Returns service definitions for service name(s)
    @param svcs name or list of names of service
    """
    from pyon.core.bootstrap import obj_registry

    if not getattr(svcs, '__iter__', False) and op is not None:
        svcdef = obj_registry.services_by_name[svcs]
        print "Service definition for: %s (version %s) operation %s" % (svcs, svcdef.version or 'ND', op)
        print "".join([str(m) for m in svcdef.methods if m.op_name == op])
        return svcdef

    elif svcs is not None:
        if not getattr(svcs, '__iter__', False):
            svcs = (svcs,)
        for svcname in svcs:
            svcdef = obj_registry.services_by_name[svcname]
            svcops = "\n     ".join(sorted([smd.op_name for smd in svcdef.methods]))
            print "Service definition for: %s (version %s)" % (svcname, svcdef.version or 'ND')
            print "ops: %s" % (svcops)
            return svcdef

    else:
        print "List of defined services"
        print "------------------------"
        from pyon.core.bootstrap import obj_registry

        for svcname in sorted(obj_registry.services_by_name.keys()):
            svcdef = obj_registry.services_by_name[svcname]
            print "%s %s" % (svcname, svcdef.version)

        print "\nType svc_defs('name') or svc_defs(['name1','name2']) for definition"
        return None

def obj_defs(ob=None):
    """Returns object definitions for object name(s)
    @param ob name or list of names of object
    """
    from pyon.core.bootstrap import obj_registry

    if ob is not None:
        print "Object definition for: %s\n" % ob

        if not getattr(ob, '__iter__', False):
            ob = (ob,)
        for o in ob:
            print obj_registry.instances_by_name[o]

    else:
        print "List of defined objects"
        print "-----------------------"
        onames = sorted(obj_registry.instances_by_name.keys())
        print pprint_list(onames, -1, 1, 2)
        print "\nType obj_defs('name') or obj_defs(['name1','name2']) for definition"

def type_defs(ob=None):
    """Returns object type definitions for object name(s)
    @param ob name or list of names of object
    """
    from pyon.core.bootstrap import obj_registry

    if ob is not None:
        print "Type definition for: %s\n" % ob

        if not getattr(ob, '__iter__', False):
            ob = (ob,)
        for o in ob:
            print obj_registry.type_by_name[o]

    else:
        print "List of defined objects"
        print "-----------------------"
        tnames = sorted(obj_registry.type_by_name.keys())
        print pprint_list(tnames, -1, 1, 2)
        print "\nType type_defs('name') or type_defs(['name1','name2']) for definition"

def lsdir(qname='/'):
    from pyon.directory.directory import Directory
    ds = Directory()
    delist = ds.find_entries(qname)
    print "\n".join(["%s: %s" % (de._id, de.attributes) for de in delist])

def ionhelp():
    print "ION R2 CC interactive shell"
    print
    print "Available functions: %s" % ", ".join(sorted([func.__name__ for func in public_api]))
    print "Available variables: %s" % ", ".join(sorted(public_vars.keys()))

# This defines the public API of functions
public_api = [ionhelp,ps,procs,ms,apps,svc_defs,obj_defs,type_defs,lsdir]
public_vars = None

def get_proc():
    from pyon.util.containers import DotDict
    procs = DotDict(container.proc_manager.procs)
    pn = DotDict(container.proc_manager.procs_by_name)
    return procs, pn

def define_vars():
    if public_vars: return public_vars
    from pyon.core.bootstrap import CFG, sys_name, obj_registry
    cc = container
    proc, pn = get_proc()

    return locals()

def get_shell_api(cc):
    """Returns an API to introspect and manipulate the container
    @retval dict that can be added to locals() namespace
    """
    global container
    global public_vars
    container = cc

    ns_dict = dict()
    for func in public_api:
        ns_dict[func.__name__] = func
    public_vars = define_vars()
    ns_dict.update(public_vars)

    return ns_dict