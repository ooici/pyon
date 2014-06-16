#!/usr/bin/env python

__author__ = 'Brian McKenna'


from nose.plugins.attrib import attr
from unittest import SkipTest
from mock import Mock, patch, ANY

from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import IonUnitTestCase

from pyon.datastore.datastore_query import DatastoreQueryBuilder
from pyon.datastore.postgresql.pg_query import PostgresQueryBuilder

import interface.objects

@attr('UNIT', group='datastore')
class PostgresDataStoreUnitTest(IonUnitTestCase):

    def test_wkt(self):
        """ unit test to verify the DatastoreQuery to PostgresQuery to SQL translation for PostGIS WKT """
        
        wkt = 'POINT(-72.0 40.0)'
        buf = 0.1
        
        # PostgresQueryBuilder - WKT (no buffer)
        qb = DatastoreQueryBuilder()
        qb.build_query(where=qb.overlaps_geom(qb.RA_GEOM_LOC,wkt,0.0))
        pqb = PostgresQueryBuilder(qb.get_query(), 'test')
        self.assertEquals(pqb.get_query(),"SELECT id,doc FROM test WHERE ST_Intersects(geom_loc,ST_GeomFromEWKT('SRID=4326;POINT(-72.0 40.0)'))")

        qb = DatastoreQueryBuilder()
        qb.build_query(where=qb.contains_geom(qb.RA_GEOM_LOC,wkt,0.0))
        pqb = PostgresQueryBuilder(qb.get_query(), 'test')
        self.assertEquals(pqb.get_query(),"SELECT id,doc FROM test WHERE ST_Contains(geom_loc,ST_GeomFromEWKT('SRID=4326;POINT(-72.0 40.0)'))")

        qb = DatastoreQueryBuilder()
        qb.build_query(where=qb.within_geom(qb.RA_GEOM_LOC,wkt,0.0))
        pqb = PostgresQueryBuilder(qb.get_query(), 'test')
        self.assertEquals(pqb.get_query(),"SELECT id,doc FROM test WHERE ST_Within(geom_loc,ST_GeomFromEWKT('SRID=4326;POINT(-72.0 40.0)'))")

        # PostgresQueryBuilder - WKT (with buffer)
        qb = DatastoreQueryBuilder()
        qb.build_query(where=qb.overlaps_geom(qb.RA_GEOM_LOC,wkt,buf))
        pqb = PostgresQueryBuilder(qb.get_query(), 'test')
        self.assertEquals(pqb.get_query(),"SELECT id,doc FROM test WHERE ST_Intersects(geom_loc,ST_Buffer(ST_GeomFromEWKT('SRID=4326;POINT(-72.0 40.0)'), 0.100000))")

        qb = DatastoreQueryBuilder()
        qb.build_query(where=qb.contains_geom(qb.RA_GEOM_LOC,wkt,buf))
        pqb = PostgresQueryBuilder(qb.get_query(), 'test')
        self.assertEquals(pqb.get_query(),"SELECT id,doc FROM test WHERE ST_Contains(geom_loc,ST_Buffer(ST_GeomFromEWKT('SRID=4326;POINT(-72.0 40.0)'), 0.100000))")

        qb = DatastoreQueryBuilder()
        qb.build_query(where=qb.within_geom(qb.RA_GEOM_LOC,wkt,buf))
        pqb = PostgresQueryBuilder(qb.get_query(), 'test')
        self.assertEquals(pqb.get_query(),"SELECT id,doc FROM test WHERE ST_Within(geom_loc,ST_Buffer(ST_GeomFromEWKT('SRID=4326;POINT(-72.0 40.0)'), 0.100000))")