#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from pyon.util.log import log

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

    def datastore_exists(self, datastore_name=""):
        """
        Indicates whether named data store currently exists.
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

    def create(self, object, object_id=None, datastore_name=""):
        """"
        Persist a new Ion object in the data store. An '_id' and initial
        '_rev' value will be added to the doc.
        """
        pass

    def create_doc(self, object, object_id=None, datastore_name=""):
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
            [[<field>, <logical constant>, <value>], <and>|<or>, ...]

        For example, to find all objects of type 'foo':
            [['type_', DataStore.EQUAL, 'foo']]

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
            [['type_', DataStore.EQUAL, 'foo'], DataStore.AND, ['name', DataStore.EQUAL, 'bar']]

        In SQL, this is equivalent to:
            select * from datastore_name where type = 'foo' and name = 'bar'

        This function returns IonObjects
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
            [['type_', DataStore.EQUAL, 'UserInfo'], DataStore.AND, ['name', DataStore.EQUAL, 'foo']], 'roles'

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
            [['type_', DataStore.EQUAL, 'foo'], DataStore.AND, ['name', DataStore.EQUAL, 'bar']]

        This function returns IonObjects
        """
        pass

    def find_by_association_doc(self, criteria=[], association="", datastore_name=""):
        """
        Same as the find_by_association method except that this function returns raw doc dicts
        """
        pass

    def resolve_association(self, subject="", predicate="", object="", datastore_name=""):
        """
        Generic association query function that allows queries for associations
        by subject, predicate and/or object.  Examples:

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
            [(IonObject, <predicate>, IonObject), ...]
        """
        pass

    def resolve_association_doc(self, subject="", predicate="", object="", datastore_name=""):
        """
        Same as the resolve_association_tuple method except that this function returns
        a set of tuples in the form
            [({}, <predicate>, {}), ...]
        """
        pass

    def create_association(self, subject_id='', predicate='', object_id=''):
        """
        Create an association between two IonObjects with a given predicate
        """
        sub = self.read(subject_id)
        obj = self.read(object_id)
        from pyon.public import IonObject
        assoc = IonObject("Association",s=subject_id, st=type(sub).__name__, p=predicate, o=object_id, ot=type(obj).__name__)
        return self.create(assoc)

    def delete_association(self, association_id=''):
        """
        Delete an association between two IonObjects
        """
        assoc = self.read(association_id)
        return self.delete(assoc)

    def find_associations(self, subject_id=None, predicate=None, object_id=None):
        if subject_id == predicate == object_id == None: raise Exception("find_associations: no args")

        search1 = [['type_','==','Association']]
        if subject_id:
            search1.append(0)
            search1.append(['s','==',subject_id])

        if object_id:
            search1.append(0)
            search1.append(['o','==',object_id])

        if predicate:
            search1.append(0)
            search1.append(['p','==',predicate])

        assoc_list = self.find(search1)
        log.debug("find_associations(sub_id=%s, pred=%s, obj_id=%s) found %s associations" % (subject_id, predicate, object_id, len(assoc_list)))
        return assoc_list

    def find_objects(self, subject_id, predicate=None):
        # HACK until triple store is in place
        # Step 1: Find associations
        assoc_list = self.find_associations(subject_id, predicate)

        # Step 2: Find destinations
        search2 = []
        for assoc in assoc_list:
            if search2:
                search2.append(1)
            search2.append(['_id','==',assoc.o])
        obj_list = self.find(search2)
        log.debug("find_objects(sub_id=%s, pred=%s) found %s objects" % (subject_id, predicate, len(obj_list)))
        return obj_list

    def find_subjects(self, object_id, predicate=None):
        # HACK until triple store is in place
        # Step 1: Find associations
        assoc_list = self.find_associations(None, predicate, object_id)

        # Step 2: Find destinations
        search2 = []
        for assoc in assoc_list:
            if search2:
                search2.append(1)
            search2.append(['_id','==',assoc.s])
        subj_list = self.find(search2)
        log.debug("find_subjects(obj_id=%s, pred=%s) found %s subjects" % (object, predicate, len(subj_list)))
        return subj_list
