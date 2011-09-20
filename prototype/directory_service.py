#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from pyon.directory.directory import Directory
from pyon.util.log import log

from interface.services.idirectory_service import BaseDirectoryService

class DirectoryService(BaseDirectoryService):

    def __init__(self, config_params={}):
        log.debug("In __init__")
        pass

    def delete(self):
        """
        Method to delete directory.  Delete occurs as side effect
        of deleting the underlying data store.
        TODO: Change this functionality in the future?
        """
        log.debug("Deleting data store and Directory")
        try:
            self.clients.datastore.delete_datastore()
        except NotFoundError:
            pass

    def create(self):
        """
        Method which will creat the underlying data store and
        persist an empty Directory object.
        """
        log.debug("Creating data store and Directory")
        self.clients.datastore.create_datastore()

        # Persist empty Directory object
        directory_obj = IonObject('Directory')
        createTuple = self.clients.datastore.create(directory_obj)

        # Save document id for later use
        log.debug("Saving Directory object id %s" % str(createTuple[0]))
        self.obj_id = createTuple[0]

    def find_dict(self, parent):
        """
        Helper method that reads the Directory object from the data store
        and then traverses the dict of dicts to find the desired parent
        dict within the directory hierarchy.
        """
        log.debug("Looking for parent dict %s" % str(parent))
        directory = self.clients.datastore.read(self.obj_id)

        # Get the actual dict of dicts from the object.
        parent_dict = directory.content
        log.debug("Root Directory dict content %s" % str(parent_dict))

        # Traverse as necessary.
        if parent == '/':
            # We're already at the root.
            log.debug("Root Directory is desired parent.")
            pass
        else:
            for pathElement in parent.split('/'):
                if pathElement == '':
                    # slash separator, ignore.
                    pass
                else:
                    log.debug("Intermediate Directory path element %s" % str(pathElement))
                    try:
                        parent_dict = parent_dict[pathElement]
                        log.debug("Intermediate Directory dict content %s" % str(parent_dict))
                    except KeyError:
                        log.debug("Intermediate Directory dict doesn't exist, creating.")
                        parent_dict[pathElement] = {}
                        parent_dict = parent_dict[pathElement]
        return directory, parent_dict

    def read(self, parent='/', key='foo'):
        """
        Read key/value pair(s) residing in directory at parent
        node level.
        """
        log.debug("Reading content at path %s" % str(parent))
        directory, parent_dict = self.find_dict(parent)
        if key is None:
            return parent_dict

        try:
            val = parent_dict[key]
        except KeyError:
            # TODO raise some exception
            pass

        return val

    def add(self, parent='/', key='foo', value={}):
        """
        Add a key/value pair to directory below parent
        node level.
        """
        log.debug("Adding key %s and value %s at path %s" % (key, str(value), parent))
        directory, parent_dict = self.find_dict(parent)

        # Add key and value, throwing exception if key already exists.
        if key in parent_dict:
            # TODO raise some exception
            pass

        parent_dict[key] = value
        self.clients.datastore.update(directory)
        return value

    def update(self, parent='/', key='foo', value={}):
        """
        Update key/value pair in directory at parent
        node level.
        """
        log.debug("Updating key %s and value %s at path %s" % (key, str(value), parent))
        directory, parent_dict = self.find_dict(parent)

        # Replace value, throwing exception if key not found.
        try:
            val = parent_dict[key]
        except KeyError:
            # TODO raise some exception
            pass

        parent_dict[key] = value
        self.clients.datastore.update(directory)
        return value

    def remove(self, parent='/', key='foo'):
        """
        Remove key/value residing in directory at parent
        node level.
        """
        log.debug("Removing content at path %s" % str(parent))
        directory, parent_dict = self.find_dict(parent)
        try:
            val = parent_dict.pop(key)
            self.clients.datastore.update(directory)
        except KeyError:
            raise KeyNotFoundError
        return val
