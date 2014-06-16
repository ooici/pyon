#!/usr/bin/env python

__author__ = 'Adam R. Smith'

from gevent import monkey; monkey.patch_all()
from compass.client import CompassException, Server, ADMIN
import simplejson as json
import time

from pyon.util.async import *

#import compass
#compass.request.DEBUG = True

import httplib2
#Monkey-patch httplib2 to fix an issue in OrientDB with case-sensitive headers
_orig_request = getattr(httplib2.Http, '_request')
def _request(self, conn, host, absolute_uri, request_uri, method, body, headers, redirections, cachekey):
    headers = {key.title():val for key,val in headers.iteritems()}
    return _orig_request(self, conn, host, absolute_uri, request_uri, method, body, headers, redirections, cachekey)
setattr(httplib2.Http, '_request', _request)

if __name__ == '__main__':
    @asyncf
    def main():
        try:
            username = 'root'
            password = 'BA7492ECB7D8B5204ACB962DEFA978D8F550C476D73F9F3036EE2AA3D6EC6A63'
            url = 'http://localhost:2480'
            #username, password = 'admin', 'admin'
            server = Server(url=url, username=username, password=password)
        except CompassException as ex:
            print ex

        # COMPLETE AND UTTER FAILURE! Couldn't even successfully create a database.
        #db = server.database(name='ion_test', create=True, credentials=(username, password))
        db = server.database(name='ion_test')
        #db.delete()
        try:
            node_cls = db.klass(name='Node', create=False)
        except CompassException:
            node_cls = db.klass(name='Node', create=True)

        time_start = time.time()
        doc_count = 500
        docs = wait([spawn(db.document, class_name='Node', name ='node-%d' % i) for i in xrange(doc_count)])
        #print docs
        #for doc in docs:
        #    doc
        #[doc.delete() for doc in docs]

        time_diff = time.time() - time_start
        print 'Took %.2f seconds' % (time_diff)

    main()
