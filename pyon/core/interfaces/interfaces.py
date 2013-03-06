#!/usr/bin/env python

"""Script to store configuration and interfaces into the directory and resource registry"""

__author__ = 'Seman Said, Michael Meisinger'

from copy import deepcopy
import os
from collections import OrderedDict

from pyon.core.path import list_files_recursive
from pyon.datastore.couchdb.couchdb_standalone import CouchDataStore
from pyon.ion.directory_standalone import DirectoryStandalone
from pyon.ion.resregistry_standalone import ResourceRegistryStandalone


class InterfaceAdmin:
    """
    Administrates work with interfaces in the datastore
    """

    DIR_RESFILES_PATH = "/Config"
    DIR_CONFIG_PATH = "/Config"

    def __init__(self, sysname, config=None):
        self.sysname = sysname
        self.config = config
        self.dir = DirectoryStandalone(sysname=self.sysname, config=config)
        self.rr = ResourceRegistryStandalone(sysname=self.sysname, config=config)
        self._closed = False

    def close(self):
        self.dir.close()
        self.dir = None
        self.rr.close()
        self.rr = None
        self._closed = True

    def __del__(self):
        if not self._closed:
            print "WARNING: Call close() on InterfaceAdmin (and datastores)"

    def create_core_datastores(self):
        """
        Main entry point into creating core datastores
        """
        ds = CouchDataStore(config=self.config, scope=self.sysname)
        datastores = ['resources','events']
        count = 0
        for local_dsn in datastores:
            if not ds.exists_datastore(local_dsn):
                ds.create_datastore(local_dsn)
                count += 1
                # NOTE: Views and other datastores are created by containers' DatastoreManager
        print "store_interfaces: Created %s datastores..." % count


    def store_config(self, system_cfg):
        """
        Main entry point into storing system config
        """
        de = self.dir.lookup(self.DIR_CONFIG_PATH + "/CFG")
        if de:
            #print "store_interfaces: WARN: Config already exists. Overwrite"
            return
        print "store_interfaces: Storing system config in directory..."
        self.dir.register(self.DIR_CONFIG_PATH, "CFG", **deepcopy(system_cfg))

    def store_interfaces(self, object_definition_file=None,
                         service_definition_file=None, idempotent=False):
        """
        Main entry point into storing interfaces
        """
        self.idempotent = idempotent
        self.bulk_entries = {}
        self.bulk_resources = []
        self.serial_num = 1

        if object_definition_file:
            self.store_object_interfaces(file=object_definition_file)
        elif service_definition_file:
            self.store_service_interfaces(file=service_definition_file)
        else:
            if self.idempotent:
                de = self.rr.find_by_type("ServiceDefinition", id_only=True)
                if de:
                    #print "store_interfaces: Interfaces already stored. Ignoring"
                    return
            # load all files
            self.store_object_interfaces()
            self.store_service_interfaces()
            self.store_config_files()

        self._register_bulk()

    def store_object_interfaces(self, file=None):
        #print "\nStoring object interfaces in datastore..."
        if file and os.path.exists(file):
            self._load_object_files([file])
        elif file:
            print "store_interfaces: Error couldn't find the file path\n"
        else:
            data_yaml_filenames = list_files_recursive('obj/data', '*.yml', ['ion.yml', 'resource.yml', 'shared.yml'])
            self._load_object_files(data_yaml_filenames)

    def _load_object_files(self, filenames):
        serial_num = 1
        for file_path in filenames:
            objs = OrderedDict()
            class_content = ''

            # Open and read data model definition file
            with open(file_path, 'r') as f:
                file_content_str = f.read()

            first_time = True
            for line in file_content_str.split('\n'):
                if len(line) > 0 and (line[0].isalpha()):
                    if not first_time:
                        objs[classname] = class_content
                        class_content = ""
                    else:
                        first_time = False
                    classname = line.split(':')[0]
                    class_content += line + "\n"
                else:
                    class_content += line + "\n"
            objs[classname] = class_content

            for key in objs.keys():
                obj_type = self._create_object_type(key, objs[key], serial_num)
                self.bulk_resources.append(obj_type)
                serial_num += 1

    def store_service_interfaces(self, file=None):
        #print "\nStoring service interfaces in datastore..."
        if file and os.path.exists(file):
            self._load_service_files([file])
        elif file:
            print "store_interfaces: Error couldn't find the file path\n"
        else:
            service_yaml_filenames = list_files_recursive('obj/services', '*.yml')
            self._load_service_files(service_yaml_filenames)

    def _load_service_files(self, filenames):
        for file_path in filenames:
            objs = {}
            with open(file_path, 'r') as f:
                file_content_str = f.read()
            for line in file_content_str.split('\n'):
                if line[:5] == "name:":
                    key = line.split()[1]
                    objs[key] = file_content_str

            if not objs:
                print "\n\n=====ERROR===== Can't find object name for: ", file_path

            for key in objs.keys():
                svc_def = self._create_service_definition(key, objs[key], file_path)
                self.bulk_resources.append(svc_def)

    def store_config_files(self):
        #print "\nStoring system res files in datastore..."
        resource_filenames = list_files_recursive('res/config', '*.yml')
        self._load_config_files(resource_filenames)

    def _load_config_files(self, filenames):
        for file_path in filenames:
            with open(file_path, 'r') as f:
                file_content_str = f.read()
            objs = {}
            objs[os.path.basename(file_path)] = file_content_str

            for key in objs.keys():
                self.bulk_entries[(self.DIR_RESFILES_PATH, key)] = dict(file_path=file_path, definition=objs[key])

    def _create_object_type(self, name, definition, definition_order):
        return dict(type_="ObjectType", name=name, definition=definition, definition_order=definition_order)

    def _create_service_definition(self, name, definition, namespace):
        return dict(type_="ServiceDefinition", name=name, definition=definition, namespace=namespace)

    def _register_bulk(self):
        print "store_interfaces: Storing %s entries in directory..." % len(self.bulk_entries)
        entries = [(path, key, attrs) for ((path, key), attrs) in self.bulk_entries.iteritems()]
        res = self.dir.register_mult(entries)
        self.bulk_entries = {}

        print "store_interfaces: Storing %s resources in registry..." % len(self.bulk_resources)
        res = self.rr.create_mult(self.bulk_resources)
        self.bulk_resources = []

        print "store_interfaces: Storing interfaces successful"

#
#def change_config():
#    if self.event_pub and bootstrap.container_instance and bootstrap.container_instance.node:
#        if parent.startswith("/Config"):
#            self.event_pub.publish_event(event_type="ContainerConfigModifiedEvent",
#                origin="Directory")
"""
        self._assert_existence("/", "Agents",
            description="Running agents are registered here")

        self._assert_existence("/", "Config",
            description="System configuration is registered here")

        self._assert_existence("/", "Containers",
            description="Running containers are registered here")

        self._assert_existence("/", "ObjectTypes",
            description="ObjectTypes are registered here")

        self._assert_existence("/", "Org",
            description="Org specifics are registered here",
            is_root=self.is_root)

        self._assert_existence("/Org", "Resources",
            description="Shared Org resources are registered here")

        self._assert_existence("/", "ResourceTypes",
            description="Resource types are registered here")

        self._assert_existence("/", "ServiceInterfaces",
            description="Service interface definitions are registered here")

        self._assert_existence("/", "Services",
            description="Service instances are registered here")
"""
