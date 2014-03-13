This directory contains a PostgreSQL datastore implementation for the Pyon container.
See https://confluence.oceanobservatories.org/display/CIDev/Postgres+Datastore

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
- Check connection DSN credentials to validate correct config for both users
- ts_created/ts_updated bigint
- Connection reset when database restarted
- support descending order for all finds
- drop database timeout (concurrent users exist) does not raise exception in clear_couch
- Make geospatial handling more modular, less hardcoded
- find_associations return retired associations
- trigger vacuum analyze
- postgres connection error better distinction and message

FUTURE FEATURES:
- deleted column for resources (instead of using the lcstate==DELETED)
- More advanced order by queries
- Replace string concatenation when constructing long statements
- clear_couch_util ugly and misnamed. Should also use the code in the datastore class
- Referential integrity support
- Investigate distributed transactions (XA)
- history support by copying into separate history table
- specific views for resource types and associations
- Consider SQLAlchemy
- update_mult
- Read only datastore with different connection

OPEN QUESTIONS:
- EXPLAIN ANALYZE queries
- list_datastores() must maintain compatible result, prefixing database with sysname (because of framework code)
- Use msgpack and BYTEA for object serialization instead of json and custom accessor functions?
- rewrite association queries as select * from resources where id in (select from assoc)
