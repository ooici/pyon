This directory contains a PostgreSQL datastore implementation for the Pyon container.

REQUIREMENTS/COMPATIBILITY:
- PostgreSQL 9.2.0 or higher
- PostGIS 2.1.0 or higher
- psycopg2 Python client 2.5 or higher (needs to do automatic JSON decoding)

BASIC FUNCTIONALITY:
- Creates one PG database per sysname
- Creates all objects in the default "public" schema
- Creates a set of tables, indexes, functions based on pre-defined SQL scripts
- Uses configured users to connect: admin user for DDL statements and regular user otherwise
- Uses connection pool and psycopg2 to connect to PG

ISSUES/MISSING FEATURES:
- Replace string concatenation when constructing long statements
- clear_couch_util ugly and misnamed
- support descending order for all finds
- create_mult is (ab)used for both create and update in one call by preload! Fix test doing both
- drop database timeout (concurrent users exist) does not raise exception in clear_couch
- Make geospatial handling more modular, less hardcoded
- find_associations return retired associations
- trigger vacuum analyze
- postgres connection error better distinction and message
- Connection reset when database restarted
- ts_created/ts_updated bigint

FUTURE FEATURES:
- Referential integrity support
- Investigate distributed transactions (XA)
- history support by copying into separate history table
- specific views for resource types and associations
- Consider SQLAlchemy
- update_mult
- Read only datastore with different connection
- find_resources_mult

OPEN QUESTIONS:
- FILESYSTEM datastore used by preservation MS or not?
- EXPLAIN ANALYZE queries
- check query_view implementation (seems to be unused)
- Use postgres 9.3 json operators
- Rewrite some of the json functions
- list_datastores() must maintain compatible result, prefixing database with sysname (because of framework code)
- Use msgpack for object serialization instead of json and custom accessor functions?
- rewrite association queries as select * from resources where id in (select from assoc)
