#!/usr/bin/env python

"""Datastore query expressions.

This module provides constants and a factory class to compose structured queries against a datastore,
including resources, events, objects datastores. It is inspired by the capabilities of a SQL query language
such as Postgres+PostGIS, but is not targeted at a specific DMBS. Specific mapping classes can then provide
a mapping to the datastore technology.
"""

__author__ = 'Michael Meisinger'

import datetime
import time

from pyon.core.exception import BadRequest
from pyon.datastore.datastore_common import DataStore


class DatastoreQueryConst(object):
    """Constants for generic datastore query expressions"""

    # Expression
    EXP_PREFIX = "exp:"
    EXP_AND = EXP_PREFIX + "and"
    EXP_OR = EXP_PREFIX + "or"
    EXP_NOT = EXP_PREFIX + "not"

    # Operators
    OP_PREFIX = "op:"                # Simple operators prefix
    OP_EQ = OP_PREFIX + "eq"         # Find objects with special attr equal to given value
    OP_NEQ = OP_PREFIX + "neq"       # Find objects with special attr not equal to given value
    OP_LT = OP_PREFIX + "lt"         # Find objects with special attr lower than given value
    OP_LTE = OP_PREFIX + "lte"       # Find objects with special attr lower than or equal given value
    OP_GT = OP_PREFIX + "gt"         # Find objects with special attr greater than given value
    OP_GTE = OP_PREFIX + "gte"       # Find objects with special attr greater than or equal given value
    OP_LIKE = OP_PREFIX + "like"     # Find objects with special attr matching given pattern (case sensitive)
    OP_ILIKE = OP_PREFIX + "ilike"   # Find objects with special attr matching given pattern (case insensitive)
    OP_FUZZY = OP_PREFIX + "fuzzy"   # Find objects with special attr similar to given value (case insensitive)
    OP_REGEX = OP_PREFIX + "regex"   # Find objects with special attr matching given value POSIX regex
    OP_IREGEX = OP_PREFIX + "iregex" # Find objects with special attr matching given value POSIX regex (case insensitive)

    XOP_PREFIX = "xop:"                     # Extended operators prefix
    XOP_IN = XOP_PREFIX + "in"              # Find objects with attr equal to one of given values
    XOP_BETWEEN = XOP_PREFIX + "between"    # Find objects with attr between 2 given values (inclusive)
    XOP_ATTLIKE = XOP_PREFIX + "attlike"    # Find objects with attr matching given pattern (case sensitive)
    XOP_ATTILIKE = XOP_PREFIX + "attilike"  # Find objects with attr matching given pattern (case insensitive)
    XOP_ALLMATCH = XOP_PREFIX + "allmatch"  # Find objects where values occurs within any of the first level attributes
    XOP_ISTYPE = XOP_PREFIX + "istype"      # Find objects with type or base type equal to given value (e.g. events)

    GOP_PREFIX = "gop:"                               # Geospatial operators prefix
    GOP_OVERLAPS_BBOX = GOP_PREFIX + "overlaps"       # Find objects with geometry overlapping given bbox
    GOP_WITHIN_BBOX = GOP_PREFIX + "within"           # Find objects with geometry within given bbox
    GOP_CONTAINS_BBOX = GOP_PREFIX + "contains"       # Find objects with geometry containing given bbox

    GOP_OVERLAPS_GEOM = GOP_PREFIX + "overlaps_geom"  # Find objects with geometry overlapping given WKT geometry
    GOP_WITHIN_GEOM = GOP_PREFIX + "within_geom"      # Find objects with geometry within given WKT geometry
    GOP_CONTAINS_GEOM = GOP_PREFIX + "contains_geom"  # Find objects with geometry containing given WKT geometry

    ROP_PREFIX = "rop:"                               # Range operators prefix
    ROP_OVERLAPS_RANGE = ROP_PREFIX + "overlaps"      # Find objects with range overlapping given range
    ROP_WITHIN_RANGE = ROP_PREFIX + "within"          # Find objects with range containing given range
    ROP_CONTAINS_RANGE = ROP_PREFIX + "contains"      # Find objects with range containing given range

    ASSOP_PREFIX = "assop:"                           # Association operators prefix
    ASSOP_ASSOCIATED = ASSOP_PREFIX + "associated"    # Resource is associated with other resources
    ASSOP_DESCEND_O = ASSOP_PREFIX + "descend_o"      # Find all descendants of resource (object direction)
    ASSOP_DESCEND_S = ASSOP_PREFIX + "descend_s"      # Find all descendants of resource (subject direction)

    # Object, resource and event attributes
    ATT_ID = "att:id"
    ATT_TYPE = "att:type_"
    RA_NAME = "ra:name"
    RA_TS_CREATED = "ra:ts_created"
    RA_TS_UPDATED = "ra:ts_updated"
    RA_LCSTATE = "ra:lcstate"
    RA_AVAILABILITY = "ra:availability"
    RA_GEOM = "ra:geom"
    RA_GEOM_LOC = "ra:geom_loc"
    RA_VERT_RANGE = "ra:vertical_range"
    RA_TEMP_RANGE = "ra:temporal_range"
    EA_ORIGIN = "ea:origin"
    EA_ORIGIN_TYPE = "ea:origin_type"
    EA_SUB_TYPE = "ea:sub_type"
    EA_ACTOR_ID = "ea:actor_id"
    EA_TS_CREATED = RA_TS_CREATED
    AA_SUBJECT = "aa:s"
    AA_SUBJECT_TYPE = "aa:st"
    AA_OBJECT = "aa:o"
    AA_OBJECT_TYPE = "aa:ot"
    AA_PREDICATE = "aa:p"

    # Query types
    QTYPE_RES = "qt:resource"
    QTYPE_ASSOC = "qt:association"
    QTYPE_OBJ = "qt:object"

    # Order
    ORDER_ASC = "asc"
    ORDER_DESC = "desc"

    # Text comparisons
    TXT_EQUALS = "txt:equals"
    TXT_IEQUALS = "txt:iequals"
    TXT_CONTAINS = "txt:contains"
    TXT_ICONTAINS = "txt:icontains"
    TXT_MATCH = "txt:match"
    TXT_IMATCH = "txt:imatch"
    TXT_REGEX = "txt:regex"
    TXT_IREGEX = "txt:iregex"

DQ = DatastoreQueryConst
QUERY_EXP_KEY = "QUERYEXP"
QUERY_EXP_ID = "qexp_v1.0"


class DatastoreQueryBuilder(DatastoreQueryConst):
    """Helps create structured queries to the datastore"""

    def __init__(self, profile=None, datastore=None, ds_sub=None, where=None, order_by=None, id_only=False, limit=0, skip=0, **kwargs):
        self.query = {}
        self.query["QUERYEXP"] = QUERY_EXP_ID
        qargs = self.query.setdefault("query_args", {})
        qargs["profile"] = profile or DataStore.DS_PROFILE.RESOURCES
        qargs["datastore"] = datastore or DataStore.DS_RESOURCES
        qargs["ds_sub"] = ds_sub or ""
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

    # -------------------------------------------------------------------------
    # Helpers to construct query filter expressions. Nest with and_ and or_

    def where(self, where_expr, *args, **kwargs):
        """Sets the filter expression (where clause) of the query"""
        if where_expr is not None and args:
            if kwargs.get("or_filters", False):
                self.query["where"] = self.or_(where_expr, *args)
            else:
                self.query["where"] = self.and_(where_expr, *args)
        else:
            self.query["where"] = where_expr if where_expr is not None else ""

    def and_(self, *args):
        return self.op_expr(self.EXP_AND, *args)

    def or_(self, *args):
        return self.op_expr(self.EXP_OR, *args)

    def not_(self, *args):
        return self.op_expr(self.EXP_NOT, *args)

    set_filter = where
    filter_and = and_
    filter_or = or_
    filter_not = not_

    def op_expr(self, operator, *args):
        return [operator, args or []]

    def eq(self, col, value):
        colname = self._get_attname(col)
        return self.op_expr(self.OP_EQ, colname, value)

    def neq(self, col, value):
        colname = self._get_attname(col)
        return self.op_expr(self.OP_NEQ, colname, value)

    def gt(self, col, value):
        colname = self._get_attname(col)
        return self.op_expr(self.OP_GT, colname, value)

    def gte(self, col, value):
        colname = self._get_attname(col)
        return self.op_expr(self.OP_GTE, colname, value)

    def lt(self, col, value):
        colname = self._get_attname(col)
        return self.op_expr(self.OP_LT, colname, value)

    def lte(self, col, value):
        colname = self._get_attname(col)
        return self.op_expr(self.OP_LTE, colname, value)

    def in_(self, col, *args):
        colname = self._get_attname(col)
        return self.op_expr(self.XOP_IN, colname, *args)

    def like(self, col, value, case_sensitive=True):
        colname = self._get_attname(col)
        if case_sensitive:
            return self.op_expr(self.OP_LIKE, colname, value)
        else:
            return self.op_expr(self.OP_ILIKE, colname, value)

    def fuzzy(self, col, value):
        colname = self._get_attname(col)
        return self.op_expr(self.OP_FUZZY, colname, value)

    def regex(self, col, value, case_sensitive=True):
        colname = self._get_attname(col)
        if case_sensitive:
            return self.op_expr(self.OP_REGEX, colname, value)
        else:
            return self.op_expr(self.OP_IREGEX, colname, value)

    def eq_in(self, col, expr):
        """Filter to list of values if type iterable else value equality"""
        if type(expr) in (list, tuple):
            return self.in_(col, *expr)
        else:
            return self.eq(col, expr)

    def txt_cmp(self, col, value, cmpop):
        """Text comparison"""
        cmpop = cmpop or self.TXT_EQUALS
        if cmpop != self.TXT_EQUALS and type(value) in (list, tuple):
            raise BadRequest("Filter does not support list of values")
        if cmpop == self.TXT_EQUALS:
            if type(value) in (list, tuple):
                return self.in_(col, *value)
            else:
                return self.eq(col, value)
        elif cmpop == self.TXT_IEQUALS:
            return self.like(col, value, case_sensitive=False)
        elif cmpop == self.TXT_CONTAINS:
            return self.like(col, "%" + value + "%")
        elif cmpop == self.TXT_ICONTAINS:
            return self.like(col, "%" + value + "%", case_sensitive=False)
        elif cmpop == self.TXT_MATCH:
            return self.like(col, value, case_sensitive=True)
        elif cmpop == self.TXT_IMATCH:
            return self.like(col, value, case_sensitive=False)
        elif cmpop == self.TXT_REGEX:
            return self.regex(col, value, case_sensitive=True)
        elif cmpop == self.TXT_IREGEX:
            return self.regex(col, value, case_sensitive=False)
        else:
            raise BadRequest("Filter compare op not supported: %s" % cmpop)

    # --- Special operators

    def between(self, col, val1, val2):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.XOP_BETWEEN, colname, val1, val2)

    def all_match(self, value):
        return self.op_expr(self.XOP_ALLMATCH, value)

    def attr_like(self, attr, value, case_sensitive=True):
        if case_sensitive:
            return self.op_expr(self.XOP_ATTLIKE, attr, value)
        else:
            return self.op_expr(self.XOP_ATTILIKE, attr, value)

    # --- Range operators

    def overlaps_range(self, col, x1, y1):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.ROP_OVERLAPS_RANGE, colname, x1, y1)

    def contains_range(self, col, x1, y1):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.ROP_CONTAINS_RANGE, colname, x1, y1)

    def within_range(self, col, x1, y1):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.ROP_WITHIN_RANGE, colname, x1, y1)

    # --- Geospatial operators

    def overlaps_bbox(self, col, x1, y1, x2, y2):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.GOP_OVERLAPS_BBOX, colname, x1, y1, x2, y2)

    def contains_bbox(self, col, x1, y1, x2, y2):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.GOP_CONTAINS_BBOX, colname, x1, y1, x2, y2)

    def within_bbox(self, col, x1, y1, x2, y2):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.GOP_WITHIN_BBOX, colname, x1, y1, x2, y2)

    # --- Geospatial (WKT) operators

    def overlaps_geom(self, col, wkt, buf):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.GOP_OVERLAPS_GEOM, colname, wkt, buf)

    def contains_geom(self, col, wkt, buf):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.GOP_CONTAINS_GEOM, colname, wkt, buf)

    def within_geom(self, col, wkt, buf):
        self._check_col(col)
        colname = col.split(":", 1)[1]
        return self.op_expr(self.GOP_WITHIN_GEOM, colname, wkt, buf)

    # --- By association

    def associated_with(self, target=None, target_type=None, predicate=None, direction=None, target_filter=None):
        return self.op_expr(self.ASSOP_ASSOCIATED, target, target_type, predicate, direction, target_filter)

    # --- Ordering

    def order_by(self, column, sort="asc", *args):
        order_by_list = []
        if type(column) in (list, tuple):
            for col in column:
                if type(col) in (list, tuple):
                    colname, colsort = col
                    order_by_list.append((colname, colsort))
                else:
                    order_by_list.append((col, sort))
        else:
            order_by_list = [(column, sort)]

        return order_by_list

    # --- Other query parameters

    def set_skip(self, skip):
        qargs = self.query["query_args"]
        if skip is not None:
            qargs["skip"] = skip

    def set_limit(self, limit):
        qargs = self.query["query_args"]
        if limit is not None:
            qargs["limit"] = limit

    def set_id_only(self, id_only):
        qargs = self.query["query_args"]
        if id_only is not None:
            qargs["id_only"] = id_only

    def set_query_parameters(self, params):
        if not params:
            return
        self.query.setdefault("query_params", {}).update(params)

    # --- Internal functions

    def _check_col(self, col):
        profile = self.query["query_args"]["profile"]
        if profile == DataStore.DS_PROFILE.RESOURCES:
            if not (col.startswith("ra") or col.startswith("att") or col.startswith("aa")):
                raise BadRequest("Query column unknown: %s" % col)
        elif profile == DataStore.DS_PROFILE.EVENTS:
            if not (col.startswith("ea") or col.startswith("att") or col == DQ.RA_TS_CREATED):
                raise BadRequest("Query column unknown: %s" % col)

    def _get_attname(self, col):
        attname = col.split(":", 1)[-1]
        return attname

    def _make_ion_ts(self, value):
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return str(int(time.mktime(value.timetuple()) * 1000))
        if type(value) is float:
            return str(int(value))
        return str(value)

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
