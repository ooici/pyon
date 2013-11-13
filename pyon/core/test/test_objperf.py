#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from types import NoneType
import time
import copy
from nose.plugins.attrib import attr

from pyon.util.unit_test import IonUnitTestCase
from pyon.core.object import IonObjectBase
from pyon.util.log import log


def create_test_object(depth=3, breadth=10, do_list=True, do_ion=False, uvals=False, ukeys=False):
    import random, string
    from interface.objects import Resource
    num_kinds = 1 + (1 if do_list else 0) + (1 if do_ion else 0)

    def create_test_col(level=0, ot=dict):
        if level == 0:
            value = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(random.randint(0, 15)))
            if uvals and random.random() > 0.5:
                value = unicode(value + u'\u20ac')
            return value
        if ot == dict:
            res_dict = {}
            for i in xrange(breadth / num_kinds):
                key1 = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(random.randint(5, 10)))
                if ukeys and random.random() > 0.5:
                    key1 = unicode(key1 + u'\u20ac')
                res_dict[key1] = create_test_col(level-1, dict)
                if do_list:
                    key2 = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(random.randint(5, 10)))
                    if ukeys and random.random() > 0.5:
                        key2 = unicode(key2 + u'\u20ac')
                    res_dict[key2] = create_test_col(level-1, list)
                if do_ion:
                    pass
            return res_dict
        elif ot == list:
            res_list = []
            for i in xrange(breadth / num_kinds):
                res_list.append(create_test_col(level-1, dict))
                if do_list:
                    res_list.append(create_test_col(level-1, list))
                if do_ion:
                    pass
            return res_list
        elif ot == "IonObject":
            res_obj = Resource(name="TestObject %s.%s" % (level, random.randint(1000, 9999)))
            for i in xrange(breadth / num_kinds):
                pass
            return res_obj

    test_obj = create_test_col(depth, dict)
    return test_obj


def walk1(o, cb):
    """walk from prior code"""
    newo = cb(o)

    # is now or is still an iterable? iterate it.
    if isinstance(newo, dict):
        return {k: walk1(v, cb) for k, v in newo.iteritems()}

    elif hasattr(newo, '__iter__'):
        # Case list, tuple, set and other iterables
        return [walk1(x, cb) for x in newo]

    elif isinstance(newo, IonObjectBase):
        fields, set_fields = newo.__dict__, newo._schema

        for fieldname in set_fields:
            fieldval = getattr(newo, fieldname)
            newfo = walk1(fieldval, cb)
            if newfo != fieldval:
                setattr(newo, fieldname, newfo)   # Careful: setattr may be doing validation
        return newo
    else:
        return newo


BASIC_TYPE_SET = set((str, bool, int, float, long, NoneType))

def recursive_encode1(obj):
    """Recursively walks a dict/list collection and in-place encodes any unicode value in a
    dict-value/list entry to UTF8 encoded str"""
    if type(obj) is dict:
        for k, v in obj.iteritems():
            if type(v) in BASIC_TYPE_SET:
                continue
            if type(v) is unicode:
                obj[k] = v.encode("utf8")
                continue
            recursive_encode1(v)
    elif type(obj) is list:
        for i, v in enumerate(obj):
            if type(v) in BASIC_TYPE_SET:
                continue
            if type(v) is unicode:
                obj[i] = v.encode("utf8")
                continue
            recursive_encode1(v)


@attr('UNIT')
class ObjectPerfTest(IonUnitTestCase):

    def test_walk(self):
        t1 = time.time()
        test_obj = create_test_object(3, 40, do_list=True, uvals=True, ukeys=True)  # 30 for fast, 50 for slower
        t2 = time.time()
        log.info("Time create: %s", (t2-t1))

        t1 = time.time()
        o1 = copy.deepcopy(test_obj)
        t2 = time.time()
        log.info("Time deepcopy: %s", (t2-t1))

        import simplejson
        t1 = time.time()
        oj = simplejson.dumps(test_obj)
        t2 = time.time()
        log.info("Time simplejson.dumps: %s", (t2-t1))
        log.info("  len(json): %s", len(oj))

        import json
        t1 = time.time()
        oj = json.dumps(test_obj)
        t2 = time.time()
        log.info("Time json.dumps: %s", (t2-t1))

        t1 = time.time()
        o2 = simplejson.loads(oj)
        t2 = time.time()
        log.info("Time simplejson.loads: %s", (t2-t1))

        t1 = time.time()
        o2 = json.loads(oj)
        t2 = time.time()
        log.info("Time json.loads: %s", (t2-t1))

        def unicode_to_utf8(value):
            if isinstance(value, unicode):
                value = str(value.encode('utf8'))
            return value

        from pyon.core.object import walk
        t1 = time.time()
        o3 = walk(test_obj, unicode_to_utf8)
        t2 = time.time()
        log.info("Time pyon.core.object.walk / unicode: %s", (t2-t1))

        t1 = time.time()
        o4 = walk1(test_obj, unicode_to_utf8)
        t2 = time.time()
        log.info("Time walk1 / unicode: %s", (t2-t1))

        from pyon.util.containers import recursive_encode
        o2 = simplejson.loads(oj)
        t1 = time.time()
        recursive_encode(o2)
        t2 = time.time()
        log.info("Time pyon.util.containers.recursive_utf8encode: %s", (t2-t1))

        o2 = simplejson.loads(oj)
        t1 = time.time()
        recursive_encode1(o2)
        t2 = time.time()
        log.info("Time recursive_utf8encode1: %s", (t2-t1))
