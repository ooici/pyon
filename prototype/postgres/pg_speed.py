__author__ = 'mmeisinger'

import psycopg2
from psycopg2 import OperationalError, ProgrammingError, DatabaseError, IntegrityError, extensions
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time
import uuid
import json


class PostgresSpeed(object):

    def clean_up(self):
        conn1 = psycopg2.connect("dbname=postgres")
        conn1.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        try:
            with conn1.cursor() as cur:
                cur.execute("DROP DATABASE pg_test")
        except Exception as ex:
            print ex

        with conn1.cursor() as cur:
            cur.execute("CREATE DATABASE pg_test")

        conn1.close()

        self.conn = psycopg2.connect("dbname=pg_test")

    def init_test(self):
        with self.conn.cursor() as cur:
            cur.execute("CREATE TABLE resources (id varchar(300) PRIMARY KEY, rev int, doc json, type_ varchar(80), lcstate varchar(10), availability varchar(14), name varchar(300), ts_created varchar(14))")

    def clear_tables(self):
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE resources")

    def test_insert_onetrans(self, num):
        time1 = time.time()
        with self.conn.cursor() as cur:
            for i in xrange(num):
                doc_id = uuid.uuid4().hex
                doc = dict(argument1=1, other="2", more=["one", "two", "three"], totally_new=dict(something=True), id_=doc_id)
                cur.execute("INSERT INTO resources (id, rev, doc, type_, lcstate, availability, name, ts_created) VALUES (%s, 1, %s, 'Process', 'DEPLOYED', 'AVAILABLE', 'sterling_29593.1', '1381860594327')", (doc_id, json.dumps(doc)))
        time2 = time.time()
        print " insert 1 transaction: ", num, (time2-time1)

    def test_insert_onetranssave(self, num):
        time1 = time.time()
        with self.conn.cursor() as cur:
            for i in xrange(num):
                doc_id = uuid.uuid4().hex
                doc = dict(argument1=1, other="2", more=["one", "two", "three"], totally_new=dict(something=True), id_=doc_id)
                cur.execute("SAVEPOINT bulk_update")
                cur.execute("INSERT INTO resources (id, rev, doc, type_, lcstate, availability, name, ts_created) VALUES (%s, 1, %s, 'Process', 'DEPLOYED', 'AVAILABLE', 'sterling_29593.1', '1381860594327')", (doc_id, json.dumps(doc)))
        time2 = time.time()
        print " insert 1 transaction with savepoints: ", num, (time2-time1)

    def test_insert_separate(self, num):
        time1 = time.time()
        for i in xrange(num):
            with self.conn.cursor() as cur:
                doc_id = uuid.uuid4().hex
                doc = dict(argument1=1, other="2", more=["one", "two", "three"], totally_new=dict(something=True), id_=doc_id)
                cur.execute("INSERT INTO resources (id, rev, doc, type_, lcstate, availability, name, ts_created) VALUES (%s, 1, %s, 'Process', 'DEPLOYED', 'AVAILABLE', 'sterling_29593.1', '1381860594327')", (doc_id, json.dumps(doc)))
        time2 = time.time()
        print " insert separate transactions: ", num, (time2-time1)

    def test_insert_one(self, num):
        time1 = time.time()

        args = {}
        statement = "INSERT INTO resources (id, rev, doc, type_, lcstate, availability, name, ts_created) VALUES "
        for i in xrange(num):
            doc_id = uuid.uuid4().hex
            doc = dict(argument1=1, other="2", more=["one", "two", "three"], totally_new=dict(something=True), id_=doc_id)
            if i>0:
                statement += ","
            statement += "(%(id"+str(i)+")s, 1, %(doc"+str(i)+")s, 'Process', 'DEPLOYED', 'AVAILABLE', 'sterling_29593.1', '1381860594327')"
            args["id"+str(i)] = doc_id
            args["doc"+str(i)] = json.dumps(doc)


        with self.conn.cursor() as cur:
            cur.execute(statement, args)
        time2 = time.time()
        print " insert one statement: ", num, (time2-time1)


    def do_all(self):
        NUM = 100000
        self.clean_up()
        self.init_test()

        self.test_insert_one(NUM)
        self.clear_tables()

        self.test_insert_onetrans(NUM)
        self.clear_tables()

        #self.test_insert_onetranssave(NUM)
        #self.clear_tables()

        self.test_insert_separate(NUM)
        self.clear_tables()

if __name__ == '__main__':
    pgs = PostgresSpeed()
    pgs.do_all()
