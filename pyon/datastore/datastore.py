#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

class DataStore(object):
    """
    Think of this class as a database server.
    """

    EQUAL = '=='
    NOT_EQUAL = '!='
    GREATER_THAN = '>'
    GREATER_THAN_OR_EQUAL = '>='
    LESS_THAN = '<'
    LESS_THAN_OR_EQUAL = '<='

    AND = 0
    OR = 1

    def create_datastore(self, datastore_name=""):
        """
        Create a data store with the given name.  This is
        equivalent to creating a database on a database server.
        """
        pass

    def delete_datastore(self, datastore_name=""):
        """
        Delete the data store with the given name.  This is
        equivalent to deleting a database from a database server.
        """
        pass

    def list_datastores(self):
        """
        List all data stores within this data store server. This is
        equivalent to listing all databases hosted on a database server.
        """
        pass

    def info_datastore(self, datastore_name=""):
        """
        List information about a data store.  Content may vary based
        on data store type.
        """
        pass

    def list_objects(self, datastore_name=""):
        """
        List all object types existing in the data store instance.
        """
        pass

    def list_object_revisions(self, object_id, datastore_name=""):
        """
        Method for itemizing all the versions of a particular object
        known to the data store.
        """
        pass

    def create(self, object, datastore_name=""):
        """"
        Persist a new Ion object in the data store. An '_id' and initial
        '_rev' value will be added to the doc.
        """
        pass

    def create_doc(self, object, datastore_name=""):
        """"
        Persist a new raw doc in the data store. An '_id' and initial
        '_rev' value will be added to the doc.
        """
        pass

    def read(self, object_id, rev_id="", datastore_name=""):
        """"
        Fetch an Ion object instance.  If rev_id is specified, an attempt
        will be made to return that specific object version.  Otherwise,
        the HEAD version is returned.
        """
        pass

    def read_doc(self, object_id, rev_id="", datastore_name=""):
        """"
        Fetch a raw doc instance.  If rev_id is specified, an attempt
        will be made to return that specific doc version.  Otherwise,
        the HEAD version is returned.
        """
        pass

    def update(self, object, datastore_name=""):
        """
        Update an existing Ion object in the data store.  The '_rev' value
        must exist in the object and must be the most recent known object
        version. If not, a Conflict exception is thrown.
        """
        pass

    def update_doc(self, object, datastore_name=""):
        """
        Update an existing raw doc in the data store.  The '_rev' value
        must exist in the doc and must be the most recent known doc
        version. If not, a Conflict exception is thrown.
        """
        pass

    def delete(self, object, datastore_name=""):
        """
        Remove all versions of specified Ion object from the data store.
        This method will check the '_rev' value to ensure that the object
        provided is the most recent known object version.  If not, a
        Conflict exception is thrown.
        """
        pass

    def delete_doc(self, object, datastore_name=""):
        """
        Remove all versions of specified raw doc from the data store.
        This method will check the '_rev' value to ensure that the doc
        provided is the most recent known doc version.  If not, a
        Conflict exception is thrown.
        """
        pass

    def find(self, criteria=[], datastore_name=""):
        """
        Generic query function that allows searching on zero
        or more criteria represented in the following format:
            [(<field>, <logical constant>, <value>), <and>|<or>, ...]

        For example, to find all objects of type 'foo':
            [('type_', DataStore.EQUAL, 'foo')]

        Think of this as equivalent to:
            select * from datastore_name where type = 'foo'

        Possible logical values to apply are:
            EQUAL
            NOT_EQUAL
            GREATER_THAN
            GREATER_THAN_OR_EQUAL
            LESS_THAN
            LESS_THAN_OR_EQUAL

        If you specify two or more criterion, each criterion can
        be ANDed or ORed with the other criterion.  For example, to find
        objects of type 'foo' with name value 'bar', pass the
        following:
            [('type_', DataStore.EQUAL, 'foo'), DataStore.AND, ('name', DataStore.EQUAL, 'bar')]

        In SQL, this is equivalent to:
            select * from datastore_name where type = 'foo' and name = 'bar'

        This function returns AnodeObjects
        """
        pass

    def find_doc(self, criteria=[], datastore_name=""):
        """
        Same as the find method except that this function returns raw doc dicts
        """
        pass

    def find_by_association(self, criteria=[], association="", datastore_name=""):
        """
        Generic query function that allows searching on zero
        or more criteria represented in the following format:
            [(<field>, <logical constant>, <value>), ...]
        to derive a list of associated objects.  The association
        of interest is passed in the association attribute
        and should be the name of an object field.

        For example to find the roles of user 'foo' specify the following
        criteria and association:
            [('type_', DataStore.EQUAL, 'UserInfo'), DataStore.AND, ('name', DataStore.EQUAL, 'foo')], 'roles'

        Think of this as equivalent to:
            select * from datastore_name where id_ in (
                select roles from datastore_name where type = 'UserInfo' and name = 'foo'
            )

        Possible logical values to apply are:
            EQUAL
            NOT_EQUAL
            GREATER_THAN
            GREATER_THAN_OR_EQUAL
            LESS_THAN
            LESS_THAN_OR_EQUAL

        If you specify two or more criterion, each criterion can
        be ANDed or ORed with the other criterion.  For example, to find
        objects of type 'foo' with name value 'bar', pass the
        following:
            [('type_', DataStore.EQUAL, 'foo'), DataStore.AND, ('name', DataStore.EQUAL, 'bar')]

        This function returns AnodeObjects
        """
        pass

    def find_by_association_doc(self, criteria=[], association="", datastore_name=""):
        """
        Same as the find_by_association method except that this function returns raw doc dicts
        """
        pass

    def resolve_association_tuple(self, tuple=(), datastore_name=""):
        """
        Generic association query function that allows queries for associations
        by subject, predicate or object.  Examples:

        (<subject>, <predicate>, None) - returns all objects associated with
            the subject via the specified predicate
        (<subject>, None, <object>) - returns all associations between subject
            and object
        (None, <predicate>, <object>) - returns all subjects that have association
            with object via predicate
        (<subject>, <predicate>, <object>) - returns true if association exists
        (None, <predicate>, None) - returns all subjects and objects associated
            via predicate

        This function returns a set of tuples in the form
            [(AnodeObject, <predicate>, AnodeObject), ...]
        """
        pass

    def resolve_association_tuple_doc(self, tuple=(), datastore_name=""):
        """
        Same as the resolve_association_tuple method except that this function returns
        a set of tuples in the form
            [({}, <predicate>, {}), ...]
        """
        pass
