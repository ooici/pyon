#!/usr/bin/env python

"""Datastore query expressions"""

__author__ = 'Michael Meisinger'

from pyon.core.exception import BadRequest
from pyon.datastore.datastore_common import DataStore


class DatastoreQueryConst(object):

    # Expression
    EXP_AND = "exp:and"
    EXP_OR = "exp:or"
    EXP_NOT = "exp:not"

    # Operators
    OP_EQ = "op:eq"
    OP_NEQ = "op:neq"
    OP_LT = "op:lt"
    OP_LTE = "op:lte"
    OP_GT = "op:gt"
    OP_GTE = "op:gte"
    OP_LIKE = "op:like"
    OP_ILIKE = "op:ilike"
    OP_FUZZY = "op:fuzzy"
    XOP_IN = "xop:in"

    XOP_BETWEEN = "xop:between"
    XOP_ATTLIKE = "xop:attlike"
    XOP_ALLMATCH = "xop:allmatch"

    GOP_OVERLAPS_BBOX = "gop:overlaps"
    GOP_CONTAINEDBY_BBOX = "gop:containedby"
    GOP_CONTAINS_BBOX = "gop:contains"

    # Object and resource attribute
    ATT_ID = "att:id"
    ATT_TYPE = "att:type_"
    RA_NAME = "ra:name"
    RA_TS_CREATED = "ra:ts_created"
    RA_TS_UPDATED = "ra:ts_updated"
    RA_LCSTATE = "ra:lcstate"
    RA_AVAILABILITY = "ra:availability"
    RA_GEOM = "ra:geom"
    RA_GEOM_LOC = "ra:geom_loc"
    RA_GEOM_VERT = "ra:geom_vert"
    RA_GEOM_TEMP = "ra:geom_temp"


DQ = DatastoreQueryConst
QUERY_EXP_ID = "qexp_v1.0"


class DatastoreQueryBuilder(DatastoreQueryConst):
    """Helps create structured queries to the datastore"""

    def __init__(self, profile=None, datastore=None, where=None, order_by=None, id_only=False, limit=0, skip=0, **kwargs):
        self.query = {}
        self.query["QUERYEXP"] = QUERY_EXP_ID
        qargs = self.query.setdefault("query_args", {})
        qargs["profile"] = profile or DataStore.DS_PROFILE.RESOURCES
        qargs["datastore"] = datastore or DataStore.DS_RESOURCES
        self.build_query(where=where, order_by=order_by, id_only=id_only, limit=limit, skip=skip)

    def build_query(self, where=None, order_by=None, id_only=None, limit=None, skip=None, **kwargs):
        qargs = self.query["query_args"]
        if id_only is not None:
            qargs["id_only"] = id_only
        if limit is not None:
            qargs["limit"] = limit
        if skip is not None:
            qargs["skip"] = skip
        qargs.update(kwargs)
        self.query["where"] = where if where is not None else self.query.get("where", "")
        self.query["order_by"] = order_by if order_by is not None else self.query.get("order_by", {})

    def get_query_arg(self, argname, default=None):
        return self.query["query_args"].get(argname, default)

    def get_query(self):
        self.check_query(self.query)
        return self.query

    def op_expr(self, operator, *args):
        return [operator, args or []]

    def and_(self, *args):
        return self.op_expr(self.EXP_AND, *args)

    def or_(self, *args):
        return self.op_expr(self.EXP_OR, *args)

    def not_(self, *args):
        return self.op_expr(self.EXP_NOT, *args)

    def eq(self, col, value):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.OP_EQ, colname, value)

    def neq(self, col, value):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.OP_NEQ, colname, value)

    def in_(self, col, *args):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.XOP_IN, colname, *args)

    def like(self, col, value, case_sensitive=True):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        if case_sensitive:
            return self.op_expr(self.OP_LIKE, colname, value)
        else:
            return self.op_expr(self.OP_ILIKE, colname, value)

    def between(self, col, val1, val2):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.XOP_BETWEEN, colname, val1, val2)

    def fuzzy(self, col, value):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.OP_FUZZY, colname, value)

    def all_match(self, value):
        return self.op_expr(self.XOP_ALLMATCH, value)

    def attr_like(self, attr, value):
        return self.op_expr(self.XOP_ATTLIKE, attr, value)

    def overlaps_bbox(self, col, x1, y1, x2, y2):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.GOP_OVERLAPS_BBOX, colname, x1, y1, x2, y2)

    def contains_bbox(self, col, x1, y1, x2, y2):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.GOP_CONTAINS_BBOX, colname, x1, y1, x2, y2)

    def containedby_bbox(self, col, x1, y1, x2, y2):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.GOP_CONTAINEDBY_BBOX, colname, x1, y1, x2, y2)

    def order_by(self, column, asc=True, *args):
        pass

    def _check_col(self, col):
        profile = self.query["query_args"]["profile"]
        if profile == DataStore.DS_PROFILE.RESOURCES:
            if not (col.startswith("ra") or col.startswith("att")):
                raise BadRequest("Query column unknown: %s" % col)


    @classmethod
    def check_query(cls, query):
        """Check a query expression (dict) for basic compliance"""
        if not isinstance(query, dict):
            raise BadRequest("query type dict expected, not: %s" % type(query))
        if not "query_args" in query:
            raise BadRequest("query_args expected in query")
        if query["QUERYEXP"] != QUERY_EXP_ID:
            raise BadRequest("Unknown query expression language: %s" % query["query_args"]["QUERYEXP"])
        if not "where" in query:
            raise BadRequest("where expected in query")
        if not "order_by" in query:
            raise BadRequest("order_by expected in query")
