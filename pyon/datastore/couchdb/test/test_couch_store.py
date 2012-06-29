
from pyon.datastore.couchdb.couch_store import CouchStore
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr
from pyon.util.log import log
from pyon.core.bootstrap import CFG

@attr('INT', group='datastore')
class TestCouchStore(IonIntegrationTestCase):
    def setUp(self):
        log.debug("cfg %s", repr(CFG['server'].keys()))
        server=CFG['server']['couchdb']['host']
        username=CFG['server']['couchdb']['username']
        password=CFG['server']['couchdb']['password']
        self.subject = CouchStore('test-db', server, username=username, password=password, can_create=True)

    def tearDown(self):
        self.subject.drop()

    def testCreateDrop(self):
        pass

    def testInsertRead(self):
        # insert single
        doc = { 'a':'1', 'b':'2', '_id':'1' }
        self.subject.insert(doc)
#        self.assertTrue('_rev' in doc.keys())
        succ,id,doc_out = self.subject.read('1')
        for key in doc.keys():
            self.assertEquals(doc[key], doc_out[key])
        self.assertTrue('_rev' in doc_out.keys(), msg=repr(doc_out.keys()))

        # insert list
        docs = [ { 'a':'1', 'b':'2', '_id':'2' },
                 { 'a':'1', 'b':'2', '_id':'3' } ]
        self.subject.insert(docs)
        docs_out = self.subject.read(['3','1','2'])
        doc_in = docs[1]
        succ,id,doc_out = docs_out[0]
        for key in doc_in.keys():
            self.assertEquals(doc_in[key], doc_out[key], msg='out=%s'%repr(doc_out))

        # insert duplicate
        out = self.subject.insert(doc)
        self.assertFalse(out[0])
        docs = [ { 'a':'1', 'b':'2', '_id':'0' },
                 { 'a':'1', 'b':'2', '_id':'2' }, # duplicate ID
                 { 'a':'1', 'b':'2', '_id':'5' } ]
        out = self.subject.insert(docs)
        self.assertTrue(out[0][0])
        self.assertFalse(out[1][0])
        self.assertTrue(out[2][0])



    def testUpdate(self):
        docs = [ { 'a':'1', 'b':'2', '_id':'2' },
                 { 'a':'1', 'b':'2', '_id':'3' } ]
        self.subject.insert(docs)
        self.assertTrue('_rev' in docs[0])  # couchdb library updates dictionary!

        # normal update should succeed
        docs[0]['a'] = 'changed'
        docs[1]['b'] = 'changed'
        out = self.subject.update(docs)
        self.assertTrue(out[0][0])
        self.assertTrue(out[1][0])

        # missing or wrong _rev and update should fail
        del(docs[0]['_rev'])
        #                  1-1d11ff1d76bfac091a6ca550c9d0863d
        docs[1]['_rev'] = '1-1d11ff1d76bfac091a6ca550c9d0863e'

        out = self.subject.update(docs)
        self.assertFalse(out[0][0])
        self.assertFalse(out[1][0])

        # with force, should find and update latest revision
        out = self.subject.update(docs, force=True)
        self.assertTrue(out[0][0])
        self.assertTrue(out[1][0])

        # doc not in DB should fail
        doc = { 'a':'1', '_id':5 }
        out = self.subject.update(doc)
        self.assertFalse(out[0])

    def testDelete(self):
        docs = [ { 'a':'1', 'b':'2', '_id':'1' },
                 { 'a':'1', 'b':'2', '_id':'2' },
                 { 'a':'1', 'b':'2', '_id':'3' },
                 { 'a':'1', 'b':'2', '_id':'4' },
                 { 'a':'1', 'b':'2', '_id':'5' } ]
        self.subject.insert(docs)

        self.subject.delete(['2','3','4'])
        try:
            succ,id,doc = self.subject.read('3')
        except Exception,e:
            log.error('throws', exc_info=True)
            self.fail('should return, not raise exception %s'%str(e))
        self.assertFalse(succ, msg="should not be able to read deleted doc")

        docs = [ { 'a':'1', 'b':'2', '_id':'1' },
                 { 'a':'1', 'b':'2', '_id':'2' },
                 { 'a':'1', 'b':'2', '_id':'3' },
                 { 'a':'1', 'b':'2', '_id':'4' },
                 { 'a':'1', 'b':'2', '_id':'5' } ]
        self.subject.insert(docs)
        out = self.subject.delete(['0','3','6'])
        self.assertFalse(out[0][0])
        self.assertTrue(out[1][0])
        self.assertFalse(out[2][0])


    def testAttr(self):
        docYY = { '_id': 'a', '_rev': 'a' }
        docYN = { '_id': 'a'              }
        docNY = {             '_rev': 'a' }
        docNN = {                         }

        self.assertTrue(self.subject._check_attr( [docYY, docYN], '_id', True))
        self.assertFalse(self.subject._check_attr( [docYY, docNY, docYN], '_id', True))
        self.assertTrue(self.subject._check_attr( [docNY,docNN], '_id', False))
        self.assertFalse(self.subject._check_attr( [docNY,docYN,docNN], '_id', False))

