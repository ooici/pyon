#!/usr/bin/env python

"""Datastore query mapping for Postgres"""

__author__ = 'Michael Meisinger'

from pyon.core.exception import BadRequest
from pyon.datastore.datastore_query import DQ, DatastoreQueryBuilder


class PostgresQueryBuilder(object):

    # Maps operator constants to postgres operators
    OP_STR = {DQ.OP_EQ: "=",
              DQ.OP_NEQ: "<>",
              DQ.OP_LT: "<",
              DQ.OP_LTE: "<=",
              DQ.OP_GT: ">",
              DQ.OP_GTE: ">=",
              DQ.OP_LIKE: " LIKE ",
              DQ.OP_ILIKE: " ILIKE ",
              DQ.OP_FUZZY: " %% ",
              DQ.GOP_OVERLAPS_BBOX: "&&",
              DQ.GOP_CONTAINS_BBOX: "~",
              DQ.GOP_WITHIN_BBOX: "@",
              DQ.GOP_OVERLAPS_GEOM: "ST_Intersects(%s,%s)",
              DQ.GOP_CONTAINS_GEOM: "ST_Contains(%s,%s)",
              DQ.GOP_WITHIN_GEOM: "ST_Within(%s,%s)",
              DQ.ROP_OVERLAPS_RANGE: "&&",
              DQ.ROP_CONTAINS_RANGE: "@>",
              DQ.ROP_WITHIN_RANGE: "<@",
              DQ.XOP_ATTLIKE: "LIKE",
              DQ.XOP_ATTILIKE: "ILIKE",
              }

    def __init__(self, query, basetable):
        DatastoreQueryBuilder.check_query(query)
        self.query = query
        self.basetable = basetable
        self.cols = ["id"]
        if not self.query["query_args"].get("id_only", True):
            self.cols.append("doc")
        self._valcnt = 0
        self.values = {}

        self.where = self._build_where(self.query["where"])
        self.order_by = self._build_order_by(self.query["order_by"])

    def _value(self, value):
        """Saves a value for later type conformant insertion into the query"""
        self._valcnt += 1
        valname = "v" + str(self._valcnt)
        self.values[valname] = value
        return "%(" + valname + ")s"

    def _build_where(self, expr):
        if not expr:
            return ""
        op, args = expr
        if op.startswith(DQ.OP_PREFIX):
            colname, value = args
            return "%s%s%s" % (colname, self.OP_STR[op], self._value(value))
        elif op == DQ.XOP_IN:
            attname = args[0]
            values = args[1:]
            in_exp = ",".join(["%s" % self._value(val) for val in values])
            return attname + " IN (" + in_exp + ")"
        elif op == DQ.XOP_BETWEEN:
            attname, value1, value2 = args
            return "%s BETWEEN %s AND %s" % (attname, self._value(value1), self._value(value2))
        elif op == DQ.XOP_ATTLIKE or op == DQ.XOP_ATTILIKE:
            attname, value = args
            return "json_string(doc,%s) %s %s" % (self._value(attname), self.OP_STR[op], self._value(value))
        elif op == DQ.XOP_ALLMATCH:
            value = args[0]
            return "json_allattr(doc) ILIKE %s" % (self._value("%" + str(value) + "%"))
        elif op.startswith(DQ.ROP_PREFIX):
            colname, x1, y1 = args
            return "%s %s %s::numrange" % (colname, self.OP_STR[op], self._value("[%s,%s]" % (x1, y1)))
        elif op.startswith(DQ.GOP_PREFIX):
            if op.endswith('_geom'):
                colname, wkt, buf = args
                # PostGIS geometry from WKT http://postgis.net/docs/ST_GeomFromEWKT.html
                geom_from_wkt = 'ST_GeomFromEWKT(\'SRID=4326;%s\')' % (wkt)
                # if buffer specified, wrap geometry in buffer http://postgis.net/docs/ST_Buffer.html
                if buf:
                    geom_from_wkt = 'ST_Buffer(%s, %f)' % (geom_from_wkt,float(buf))
                return self.OP_STR[op] % (colname, geom_from_wkt)
            else:
               colname, x1, y1, x2, y2 = args
               return "%s %s ST_MakeEnvelope(%s,%s,%s,%s,4326)" % (colname, self.OP_STR[op],
                    self._value(x1), self._value(y1), self._value(x2), self._value(y2))
        elif op == DQ.EXP_AND:
            return "(%s)" % " AND ".join(self._build_where(ex) for ex in args)
        elif op == DQ.EXP_OR:
            return "(%s)" % " OR ".join(self._build_where(ex) for ex in args)
        elif op == DQ.EXP_NOT:
            return "NOT (%s)" % self._build_where(args[0])
        else:
            raise BadRequest("Unknown op: %s" % op)

    def _build_order_by(self, expr):
        if not expr:
            return ""
        raise BadRequest("Unknown expr: %s" % expr)

    def get_query(self):
        qargs = self.query["query_args"]
        frags = []
        frags.append("SELECT ")
        frags.append(",".join(self.cols))
        frags.append(" FROM ")
        frags.append(self.basetable)
        if self.where:
            frags.append(" WHERE ")
            frags.append(self.where)
        if self.order_by:
            frags.append(" ORDER BY ")
            frags.append(self.order_by)
        if qargs.get("limit", 0) > 0:
            frags.append(" LIMIT ")
            frags.append(str(qargs["limit"]))
        if qargs.get("skip", 0) > 0:
            frags.append(" OFFSET ")
            frags.append(str(qargs["skip"]))

        return "".join(frags)

    def get_values(self):
        return self.values
