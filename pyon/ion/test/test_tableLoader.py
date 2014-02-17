"""
@author Abird
@brief Test cases for the tableloader, 
table loader is A Service to load data products in to postgres and geoserver from the resource registry
"""

import os
from pyon.util.breakpoint import breakpoint
from pyon.public import RT, OT, PRED, LCS, CFG
from ion.services.dm.inventory.dataset_management_service import DatasetManagementService
from interface.services.dm.idataset_management_service import DatasetManagementServiceClient
from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound, Inconsistent, BadRequest
from pyon.ion.resource import PRED, RT, LCS, AS, LCE, lcstate
from pyon.util.unit_test import IonUnitTestCase
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr
import time
import psycopg2
import sys
import requests
#import tableloader

class Connection():
    def __init__(self):
        try:
            self.con = psycopg2.connect(database='postgres', user='rpsdev')
            self.cur = self.con.cursor()

            self.cur.execute('SELECT version()')
            ver = self.cur.fetchone()
            print ver

        except psycopg2.DatabaseError, e:
            #error setting up connection
            print 'Error %s' % e

        print "setup connection"

    def getConnection(self):
        return self.con


    def getCursor(self):
        return self.cur

@attr('UNIT', group='eoi')
class TestTableLoader(IonUnitTestCase):

	def setUp(self):
        pass

  	def teardown(self):
        pass

	'''
	GEOSERVER TESTS
	'''	

	def test_add_geoserver_layer(self):
        pass

	def test_remove_select_geoserver_layer(self):
		pass	

	def test_parse_rr_completely(self):
		pass

	def test_remove_all_layers(self):
		pass		


	'''
	Resource Registry TESTS
	'''		


	def test_add_fdt_layer(self):
		pass


	def test_remove_select_fdt_layer(self):
		pass	



	def test_add_all_fdt(self):
		pass
		

	def test_remove_all_fdt(self):
		pass		


	'''
	SQL TESTS
	'''	






