#!/usr/bin/env python

__author__ = 'Casey Bryant'

from nose.plugins.attrib import attr

from pyon.datastore.datastore import DatastoreManager, DatastoreFactory
from pyon.core.bootstrap import CFG
from pyon.util.int_test import IonIntegrationTestCase


@attr('INT', group='datastore')
class TestCoverage(IonIntegrationTestCase):

    def setUp(self):
        self._start_container()

    def test_coverage(self):
        datastore = DatastoreFactory.get_datastore(datastore_name='coverage', config=CFG)
        table_name = datastore._get_datastore_name()

        delete_statement = ''.join(['DELETE FROM ', table_name, " WHERE id='test'"])
        with datastore.pool.cursor(**datastore.cursor_args) as cur:
            cur.execute(delete_statement)

        statement = ''.join(['INSERT into ', table_name, " (id, name) VALUES ('test', 'insert')"])
        with datastore.pool.cursor(**datastore.cursor_args) as cur:
            cur.execute(statement)

        statement = ''.join(['SELECT id, name FROM ', table_name, " WHERE id='test'"])
        with datastore.pool.cursor(**datastore.cursor_args) as cur:
            cur.execute(statement)
            self.assertGreater(cur.rowcount, 0)
            row = cur.fetchone()
            self.assertEqual(row[0], 'test')
            self.assertEqual(row[1], 'insert')

        with datastore.pool.cursor(**datastore.cursor_args) as cur:
            cur.execute(delete_statement)

    def test_spans(self):
        datastore = DatastoreFactory.get_datastore(datastore_name='coverage_spans', config=CFG)
        table_name = datastore._get_datastore_name()

        delete_statement = ''.join(['DELETE FROM ', table_name, " WHERE span_address='test'"])
        with datastore.pool.cursor(**datastore.cursor_args) as cur:
            cur.execute(delete_statement)

        statement = ''.join(['INSERT into ', table_name, " (span_address, coverage_id, vertical_range) ",
                             "VALUES ('test', 'cov_1', '[1.0, 2.2]')"])
        with datastore.pool.cursor(**datastore.cursor_args) as cur:
            cur.execute(statement)

        statement = ''.join(['SELECT span_address, coverage_id, lower(vertical_range), upper(vertical_range) FROM ',
                             table_name, " WHERE span_address='test'"])
        with datastore.pool.cursor(**datastore.cursor_args) as cur:
            cur.execute(statement)
            self.assertGreater(cur.rowcount, 0)
            row = cur.fetchone()
            self.assertEqual(row[0], 'test')
            self.assertEqual(row[1], 'cov_1')
            self.assertEqual(float(row[2]), float(1.0))
            self.assertEqual(float(row[3]), float(2.2))

        with datastore.pool.cursor(**datastore.cursor_args) as cur:
            cur.execute(delete_statement)






