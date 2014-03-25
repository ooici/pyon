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
              DQ.OP_REGEX: " ~ ",
              DQ.OP_IREGEX: " ~* ",
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
        if self.query["query_args"].get("ds_sub", ""):
            self.basetable += "_" + self.query["query_args"]["ds_sub"]
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

    def _build_where(self, expr, table_prefix=None):
        """
        Builds a SQL filter expression string from given query expression
        @param expr  A query expression clause
        @param table_prefix  Table prefix for column names to next clause in subqueries, e.g. "MYTABLE."
        """
        if not expr:
            return ""
        table_prefix = table_prefix or ""
        op, args = expr
        if op.startswith(DQ.OP_PREFIX):
            colname, value = args
            return "%s%s%s%s" % (table_prefix, colname, self.OP_STR[op], self._value(value))
        elif op == DQ.XOP_IN:
            attname = args[0]
            values = args[1:]
            in_exp = ",".join(["%s" % self._value(val) for val in values])
            return table_prefix + attname + " IN (" + in_exp + ")"
        elif op == DQ.XOP_BETWEEN:
            attname, value1, value2 = args
            return "%s%s BETWEEN %s AND %s" % (table_prefix, attname, self._value(value1), self._value(value2))
        elif op == DQ.XOP_ATTLIKE or op == DQ.XOP_ATTILIKE:
            attname, value = args
            return "json_string(%sdoc,%s) %s %s" % (table_prefix, self._value(attname), self.OP_STR[op], self._value(value))
        elif op == DQ.XOP_ALLMATCH:
            value = args[0]
            return "json_allattr(%sdoc) ILIKE %s" % (table_prefix, self._value("%" + str(value) + "%"))
        elif op.startswith(DQ.ROP_PREFIX):
            colname, x1, y1 = args
            return "%s%s %s %s::numrange" % (table_prefix, colname, self.OP_STR[op], self._value("[%s,%s]" % (x1, y1)))
        elif op.startswith(DQ.GOP_PREFIX):
            if op.endswith('_geom'):
                colname, wkt, buf = args
                # PostGIS geometry from WKT http://postgis.net/docs/ST_GeomFromEWKT.html
                geom_from_wkt = 'ST_GeomFromEWKT(\'SRID=4326;%s\')' % (wkt)
                # if buffer specified, wrap geometry in buffer http://postgis.net/docs/ST_Buffer.html
                if buf:
                    postgis_cast = '' # we may need to cast PostGIS geography back to PostGIS geometry
                    if isinstance(buf,str):
                        if buf.lower().endswith('m'):
                            geom_from_wkt = '%s::geography' % geom_from_wkt # in meters instead of CRS units
                            buf = buf[:-1] # remove trailing 'm'
                            postgis_cast = '::geometry' # must be converted to PostGIS geometry for search/comparison
                    geom_from_wkt = 'ST_Buffer(%s, %f)%s' % (geom_from_wkt,float(buf),postgis_cast)
                return self.OP_STR[op] % (table_prefix+colname, geom_from_wkt)
            else:
               colname, x1, y1, x2, y2 = args
               return "%s %s ST_MakeEnvelope(%s,%s,%s,%s,4326)" % (table_prefix+colname, self.OP_STR[op],
                    self._value(x1), self._value(y1), self._value(x2), self._value(y2))
        elif op == DQ.EXP_AND:
            return "(%s)" % " AND ".join(self._build_where(ex, table_prefix=table_prefix) for ex in args)
        elif op == DQ.EXP_OR:
            return "(%s)" % " OR ".join(self._build_where(ex, table_prefix=table_prefix) for ex in args)
        elif op == DQ.EXP_NOT:
            return "NOT (%s)" % self._build_where(args[0], table_prefix=table_prefix)
        elif op == DQ.ASSOP_ASSOCIATED:
            target, target_type, predicate, direction, target_filter = args
            def assoc_level(lvnum, idcol):
                lvdir = direction[lvnum]
                lvpred = predicate[lvnum] if predicate and len(direction) > 1 else predicate
                ltab = "A" + str(lvnum)   # Alias name for this nesting level assoc table
                if lvdir == "S" or lvdir == "O":
                    idatt, aatt = ("s", "o") if lvdir == "S" else ("o", "s")
                    lvxpr = idcol + " IN (SELECT " + ltab + "." + idatt + " FROM " + self.basetable + "_assoc AS " + ltab + " WHERE "

                    if len(direction) <= lvnum + 1:
                        # Recursion end
                        if target and type(target) in (list, tuple):
                            lvxpr += ltab + "." + aatt + " IN ("
                            lvxpr += ",".join("%s" % self._value(targ) for targ in target) + ")"
                        elif target:
                            lvxpr += ltab + "." + aatt + "=%s" % self._value(target)
                        elif target_type and type(target_type) in (list, tuple):
                            lvxpr += ltab + "." + aatt + "t IN ("
                            lvxpr += ",".join("%s" % self._value(targ) for targ in target_type) + ")"
                        elif target_type:
                            lvxpr += ltab + "." + aatt + "t=%s" % self._value(target_type)
                            if target_filter:
                                lvxpr += " AND " + ltab + "." + aatt + " IN (SELECT id from " + self.basetable + " AS ART WHERE "
                                lvxpr += self._build_where(target_filter, table_prefix="ART.")
                                lvxpr += ")"
                        elif target_filter:
                            lvxpr += ltab + "." + aatt + " IN (SELECT id from " + self.basetable + " AS ART WHERE "
                            lvxpr += self._build_where(target_filter, table_prefix="ART.")
                            lvxpr += ")"
                        else:
                            raise BadRequest("Must provide target or target_type")

                    else:
                        # Inside recursion
                        lvxpr += assoc_level(lvnum + 1, ltab + "." + aatt)

                    # Add predicate clause
                    if lvpred and type(lvpred) in (list, tuple):
                        lvxpr += " AND " + ltab + ".p IN ("
                        lvxpr += ",".join("%s" % self._value(pr) for pr in lvpred) + ")"
                    elif lvpred:
                        lvxpr += " AND " + ltab + ".p=%s" % self._value(lvpred)

                    lvxpr += ")"

                elif lvdir == "A":
                    raise NotImplementedError()
                else:
                    raise BadRequest("Illegal association direction: %s", lvdir)
                return lvxpr

            if target and target_type:
                raise BadRequest("Cannot provide both target and target_type")
            if target and target_filter:
                raise BadRequest("Cannot provide both target and target_filter")
            direction = direction or "A"
            if predicate and len(direction) > 1 and len(direction) != len(predicate):
                raise BadRequest("Number of predicate expressions must match level of nested associations")

            # id in (select from assoc where xxx)
            xpr = assoc_level(0, "id")
            return xpr
        else:
            raise BadRequest("Unknown op: %s" % op)

    def _build_order_by(self, expr):
        if not expr:
            return ""
        order_by_list = []
        for col, colsort in expr:
            order_by_list.append("%s %s" % (col, "DESC" if colsort.lower() == "desc" else "ASC"))
        order_by = ",".join(order_by_list)
        return order_by

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
