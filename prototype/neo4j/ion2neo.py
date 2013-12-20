__author__ = 'mmeisinger'

import json

import psycopg2
from psycopg2 import OperationalError, ProgrammingError, DatabaseError, IntegrityError
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from py2neo import neo4j

DATABASE = "ion_sterling_ion"
RESOURCES = "ion_sterling_resources"
ASSOCS = "ion_sterling_resources_assoc"

class IonNeoLoader(object):

    def __init__(self):
        pass

    def connect(self):
        self.neo = neo4j.GraphDatabaseService("http://localhost:7474/db/data/")
        self.neo.clear()
        self.db = psycopg2.connect("dbname=%s" % DATABASE)

    def load_ion(self):
        cur = self.db.cursor()
        cur.execute("SELECT id, name, type_ FROM %s" % RESOURCES)
        rows = cur.fetchall()
        self.resources = [dict(id=row[0], name=row[1], type_=row[2]) for row in rows]
        print "Loaded %s resources", len(self.resources)

        cur.execute("SELECT id, s, st, p, o, ot FROM %s" % ASSOCS)
        rows = cur.fetchall()
        self.assocs = [dict(id=row[0], s=row[1], st=row[2], p=row[3], o=row[4], ot=row[5]) for row in rows]
        print "Loaded %s associations", len(self.assocs)

        cur.close()

    def create_nodes(self):
        self.res_to_nodes = {}
        batch_size = 100
        self.res_nodes = []
        for i in xrange(1 + ((len(self.resources) + batch_size - 1)/ batch_size)):
            batch = self.resources[batch_size*i:batch_size*(i+1)]
            nodes = self.neo.create(*batch)
            self.res_nodes.extend(nodes)
        self.res_to_nodes = dict(zip([res['id'] for res in self.resources], self.res_nodes))
        print "Imported %s resources" % len(self.res_to_nodes)

        for assoc in self.assocs:
            sub_node = self.res_to_nodes[assoc['s']]
            obj_node = self.res_to_nodes[assoc['o']]
            pred = assoc['p']
            sub_node.create_relationship_to(obj_node, pred)
        print "Created relationships"

    def start(self):
        self.connect()
        self.load_ion()
        self.create_nodes()
        self.close()


    def close(self):
        self.db.close()

if __name__ == '__main__':
    inl = IonNeoLoader()
    inl.start()
