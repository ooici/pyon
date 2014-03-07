#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from types import NoneType
import time
import copy
from nose.plugins.attrib import attr
from contextlib import contextmanager
import random, string
import simplejson
import msgpack, json
import pickle, cPickle

from pyon.util.unit_test import IonUnitTestCase
from pyon.core.bootstrap import IonObject
from pyon.core.object import IonObjectBase
from pyon.util.log import log

allowed_chars = string.ascii_uppercase + string.digits
POOL_SIZE = 10000
value_pool = ''.join(random.choice(allowed_chars) for x in xrange(POOL_SIZE))


def create_test_object(depth=3, breadth=10, do_dict=True, do_list=True, do_ion=False, uvals=False, ukeys=False,
                       restype="DataProduct", obj_validate=None):

    def get_value(min_len=5, max_len=10, uni=False):
        rand_pos = random.randint(0, POOL_SIZE-max_len)
        key = value_pool[rand_pos:rand_pos+random.randint(min_len, max_len)]
        if uni and random.random() > 0.5:
            key += u'\u20ac'
        return key

    def get_key():
        return get_value(uni=ukeys)

    def create_test_col(level=0, ot=dict, no_ion=False):
        if level == 0:
            return get_value(0, 15, uvals)
        if ot == dict:
            res_dict = {}
            num_kinds = 1 if do_ion and no_ion else (1 if do_dict else 0) + (1 if do_list else 0)
            for i in xrange(breadth / num_kinds):
                if do_ion and not no_ion:
                    key = get_key()
                    res_obj = IonObject(restype, name="TestObject %s.%s" % (level, key))
                    res_obj.addl = create_test_col(level-1, dict, no_ion=True)
                    res_dict[key] = res_obj
                else:
                    if do_dict:
                        res_dict[get_key()] = create_test_col(level-1, dict)
                    if do_list:
                        res_dict[get_key()] = create_test_col(level-1, list)
            return res_dict
        elif ot == list:
            res_list = []
            num_kinds = 1 if do_ion and no_ion else (1 if do_dict else 0) + (1 if do_list else 0)
            for i in xrange(breadth / num_kinds):
                if do_ion and not no_ion:
                    res_obj = IonObject(restype, name="TestObject %s.%s" % (level, random.randint(1000, 9999)))
                    res_obj.addl = create_test_col(level-1, dict, no_ion=True)
                    res_list.append(res_obj)
                else:
                    if do_dict:
                        res_list.append(create_test_col(level-1, dict))
                    if do_list:
                        res_list.append(create_test_col(level-1, list))
            return res_list
        elif ot == "IonObject":
            res_obj = IonObject(restype, name="TestObject %s.%s" % (level, random.randint(1000, 9999)))
            return res_obj

    if obj_validate is not None:
        from pyon.core.bootstrap import get_obj_registry
        old_validate = get_obj_registry().validate_setattr
        get_obj_registry().validate_setattr = obj_validate
        test_obj = create_test_col(depth, dict)
        get_obj_registry().validate_setattr = old_validate
    else:
        test_obj = create_test_col(depth, dict)

    return test_obj

@contextmanager
def time_it(msg="step"):
    t1 = time.time()
    try:
        yield
    finally:
        t2 = time.time()
        log.info("Time %s: %1.7f", msg, (t2-t1))

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
        test_obj = None
        with time_it("create"):
            test_obj = create_test_object(3, 40, do_list=True, uvals=True, ukeys=True)  # 30 for fast, 50 for slower

        with time_it("deepcopy"):
            o1 = copy.deepcopy(test_obj)

        import simplejson, json
        with time_it("simplejson.dumps"):
            oj = simplejson.dumps(test_obj)
        log.info("  len(json): %s", len(oj))

        with time_it("json.dumps"):
            oj = json.dumps(test_obj)

        with time_it("simplejson.loads"):
            o2 = simplejson.loads(oj)

        with time_it("json.loads"):
            o2 = json.loads(oj)

        def unicode_to_utf8(value):
            if isinstance(value, unicode):
                value = str(value.encode('utf8'))
            return value

        from pyon.core.object import walk
        with time_it("pyon.core.object.walk / unicode"):
            o3 = walk(test_obj, unicode_to_utf8)

        with time_it("walk1 / unicode"):
            o4 = walk1(test_obj, unicode_to_utf8)

        from pyon.util.containers import recursive_encode
        o2 = simplejson.loads(oj)
        with time_it("pyon.util.containers.recursive_utf8encode"):
            recursive_encode(o2)

        o2 = simplejson.loads(oj)
        with time_it("recursive_utf8encode1"):
            recursive_encode1(o2)

def count_objs(obj):
    counters = {}
    def _count(obj):
        counters.setdefault(type(obj), 0)
        counters[type(obj)] += 1
        if isinstance(obj, IonObjectBase):
            for k, v in obj.__dict__.iteritems():
                _count(k)
                _count(v)
        elif isinstance(obj, dict):
            for k, v in obj.iteritems():
                _count(k)
                _count(v)
        elif isinstance(obj, list):
            for v in obj:
                _count(v)
    _count(obj)
    log.info("  COUNT: %s", counters)

from pyon.core.bootstrap import get_obj_registry
from pyon.core.object import IonObjectDeserializer, IonObjectSerializer

@attr('UNIT')
class MessagingPerfTest(IonUnitTestCase):

    def test_perf(self):
        _io_serializer = IonObjectSerializer()
        _io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())

        def time_serialize(test_obj, name="?", has_ion=False):
            with time_it(name + ", serialize"):
                os = _io_serializer.serialize(test_obj)

            with time_it(name + ", deserialize"):
                os2 = _io_deserializer.deserialize(os)

            count_objs(os)

            if has_ion:
                test_obj = os

            with time_it(name + ", json.dumps"):
                oj = json.dumps(test_obj)

            with time_it(name + ", json.loads"):
                o2 = json.loads(oj)
            log.info("  len(json): %s", len(oj))

            with time_it(name + ", simplejson.dumps"):
                oj = simplejson.dumps(test_obj)

            with time_it(name + ", simplejson.loads"):
                o2 = simplejson.loads(oj)
            log.info("  len(simplejson): %s", len(oj))

            with time_it(name + ", msgpack.packb"):
                o1 = msgpack.packb(test_obj)

            with time_it(name + ", msgpack.unpackb"):
                o2 = msgpack.unpackb(o1, use_list=1)
            log.info("  len(msgpack): %s", len(o1))

            # with time_it(name + ", pickle.dumps"):
            #     op = pickle.dumps(test_obj)
            #
            # with time_it(name + ", pickle.loads"):
            #     o2 = pickle.loads(op)
            # log.info("  len(pickle): %s", len(op))
            #
            # with time_it(name + ", cPickle.dumps"):
            #     op = cPickle.dumps(test_obj)
            #
            # with time_it(name + ", cPickle.loads"):
            #     o2 = cPickle.loads(op)
            # log.info("  len(cPickle): %s", len(op))

            log.info("----------------")


        # Large nested
        with time_it("highly nested dict/list, create"):
            test_obj = create_test_object(4, 4, do_list=False, uvals=True, ukeys=True)

        time_serialize(test_obj, "highly nested dict/list")

        # Nested
        with time_it("nested dict/list, create"):
            test_obj = create_test_object(3, 40, do_list=True, uvals=False, ukeys=False)

        time_serialize(test_obj, "nested dict/list")

        # Large string
        #value = ''.join(random.choice(allowed_chars) for x in xrange(1460000))
        value = ''.join(random.choice(allowed_chars) for x in xrange(500000))

        time_serialize(value, "long string")

        # ION
        with time_it("create ion"):
            test_obj1 = create_test_object(2, 200, do_ion=True, do_list=False, do_dict=True, obj_validate=False)

        count_objs(test_obj1)
        time_serialize(test_obj1, "dict of ion nested", has_ion=True)

        from pyon.core.interceptor.interceptor import Invocation
        from pyon.core.interceptor.codec import CodecInterceptor
        from pyon.core.interceptor.encode import EncodeInterceptor
        encode = EncodeInterceptor()
        invocation = Invocation()
        invocation.message = test_obj1

        with time_it("ion object, encode"):
            encode.outgoing(invocation)

        with time_it("ion object, decode"):
            encode.incoming(invocation)

        count_objs(invocation.message)

        # ION
        with time_it("create ion unicode"):
            test_obj1 = create_test_object(2, 200, do_ion=True, do_list=False, do_dict=True, obj_validate=False, uvals=True, ukeys=True)

        count_objs(test_obj1)
        time_serialize(test_obj1, "dict of ion nested unicode", has_ion=True)


        # Create objects with validation on
        with time_it("create ion calidated"):
            test_obj1 = create_test_object(2, 200, do_ion=True, do_list=False, do_dict=True, obj_validate=True)

        count_objs(test_obj1)
        time_serialize(test_obj1, "dict of ion nested validated", has_ion=True)
