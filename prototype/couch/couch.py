#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import couchdb
from couchdb.design import ViewDefinition

import time
import random

from uuid import uuid4


def timing_val(func):
   def wrapper(*arg,**kw):
       '''source: http://www.daniweb.com/code/snippet368.html'''
       t1 = time.time()
       res = func(*arg,**kw)
       t2 = time.time()
       print "%s took %s ms" % (func.func_name, int((t2-t1)*1000))
       return (t2-t1),res,func.func_name
   return wrapper


class CouchRun(object):
    def __init__(self, host='localhost', port=5984, datastore_name='prototype', options=""):
        print 'host %s port %d data store name %s options %s' % (host, port, str(datastore_name), str(options))
        self.host = host
        self.port = port
        self.datastore_name = datastore_name
        connection_str = "http://" + host + ":" + str(port)
        print 'Connecting to couchDB server: %s' % connection_str
        self.server = couchdb.Server(connection_str)

        print 'Creating data store %s' % datastore_name
        try:
            self.server.delete(datastore_name)
        except Exception, ex:
            pass
        self.server.create(datastore_name)
        self.db = self.server[self.datastore_name]

    def create_doc(self, doc, object_id=None):
        # Assign an id to doc (recommended in CouchDB documentation)
        doc["_id"] = object_id or uuid4().hex
        # Save doc.  CouchDB will assign version to doc.
        res = self.db.save(doc)
        id, version = res
        return [id, version]

    def update_docs(self, doclist, threshold=1000):
        for slice in (doclist[i*threshold:(i+1)*threshold-1] for i in xrange(len(doclist)/threshold)):
            res = self.db.update(slice)
        residual = doclist[(len(doclist)/threshold)*threshold:]
        if residual:
            self.db.update(residual)

    def find_docs(self, map_fun):
        queryList = []
        try:
            queryList = list(self.db.query(map_fun))
        except Exception, ex:
            print ex

        results = []
        for row in queryList:
            doc = row.value
            results.append(doc)

        return results


    def _id_index(self):
        map_fun = "function(doc) {emit(doc._id, doc);}"
        return map_fun

    def _find_index(self, var, val):
        map_fun ="function(doc) {if (doc.%s == \"%s\") {emit(doc._id, doc);}}" % (var, val)
        return map_fun

    def _find_assoc(self):
        #map_fun = "function(doc) {emit(doc._id, doc);}"
        map_fun ="function(doc) {if (doc.type_ == \"Association\") {emit([doc.s, doc.p, doc.o, doc._id], null);}}"
        return map_fun

    @timing_val
    def test_insert(self, num):
        print "Testing insert doc %s times" % num
        for i in xrange(num):
            did, drev = self.create_doc(dict(num=str(i)))

    @timing_val
    def test_insertupdate(self, num, threshold=1000):
        print "Testing insert doc %s times" % num
        doc_list = [dict(num=str(i)) for i in xrange(num)]
        res = self.update_docs(doc_list, threshold)

    @timing_val
    def test_inserttriples(self, num, numassoc):
        typecnt = 50
        types = ["TYPE%s"%i for i in xrange(typecnt)]
        predcnt = 10
        preds = ["PRED%s"%i for i in xrange(predcnt)]

        print "Inserting docs: %s" % num

        self.doc_list = [dict(_id=uuid4().hex,type=types[random.randint(0,typecnt-1)],num=str(i)) for i in xrange(num)]
        self.update_docs(self.doc_list)

        print "Inserting associations: %s" % numassoc

        self.assoc_list = [dict(_id=uuid4().hex,
                           type_="Association",
                           s=self.doc_list[random.randint(0,num-1)]["_id"],
                           p=preds[random.randint(0,predcnt-1)],
                           o=self.doc_list[random.randint(0,num-1)]["_id"]) for i in xrange(numassoc)]
        self.update_docs(self.assoc_list)

        self.assoc_subject = sorted(set([ass['s'] for ass in self.assoc_list]))

    @timing_val
    def test_query(self, num, func):
        print "Testing query doc %s times, func=%s" % (num, func)
        for i in xrange(num):
            resl = self.find_docs(func)
            #print "Find result len", len(resl)

    def define_view(self, design, name, mapfunc, redfunc=None):
        self.db["_design/%s" % design] = {"views": {
                        name: {
                          "map": mapfunc,
                          #"reduce": "_count"
                        }
                      }
                    }
        #print self.create_doc(view_doc, view_doc["_id"])

    def print_view(self, design, name):
        view_name = "%s/%s" % (design, name)
        view = self.db.view(view_name)
        print "View %s rows: %s" % (view_name, len(view))

        for row in view:
            print row

    def print_view_key(self, design, name, keys, keye):
        view_name = "%s/%s" % (design, name)
        print "View direct access"
        view1 = self.db.view(view_name, inclusive_end=True, include_docs=True)
        #rows = view1[[self.assoc_subject[2]]:[self.assoc_subject[2]]]
        rows = view1[keys:keye]
        for row in rows:
            print row

    def test_views(self, design, name):
        view_name = "%s/%s" % (design, name)
        print "View direct access"
        view1 = self.db.view(view_name, inclusive_end=True)

        rows = view1[[self.assoc_subject[2]]:[self.assoc_subject[2],'ZZZ']]
        for row in rows:
            print row

        print "View again"
        rows = view1[[self.assoc_subject[3]]:[self.assoc_subject[3],'ZZZ']]
        for row in rows:
            print row

def main():
    cr = CouchRun()
    #cr.test_insert(100)

    #cr.test_insertupdate(100)

    assoc_view_name = "Assoc"
    cr.define_view(assoc_view_name, assoc_view_name, cr._find_assoc())

    cr.print_view(assoc_view_name, assoc_view_name)

    cr.test_inserttriples(50, 10)

    #print list(cr.db.view("_all_docs"))

    #cr.print_view(assoc_view_name, assoc_view_name)

    cr.test_views(assoc_view_name, assoc_view_name)

    #cr.test_query(1, cr._id_index())

    #cr.test_query(5, cr._find_index('num','5'))

    print cr.db.info()

if __name__ == "__main__":
    main()
