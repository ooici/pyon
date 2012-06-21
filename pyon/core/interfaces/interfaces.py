#!/usr/bin/env python

"""Script to store configuration and interfaces into the directory"""

__author__ = 'Seman Said, Michael Meisinger'

import inspect
import os
from collections import OrderedDict
import argparse

from pyon.core.path import list_files_recursive
from pyon.datastore.couchdb.couchdb_standalone import CouchDataStore
from pyon.ion.directory_standalone import DirectoryStandalone


class InterfaceAdmin:
    """
    Administrates work with interfaces in the datastore
    """

    DIR_OBJECTTYPES_PATH = "/ObjectTypes"
    DIR_SERVICEDEF_PATH = "/ServiceInterfaces"
    DIR_RESFILES_PATH = "/Config"
    DIR_CONFIG_PATH = "/Config"

    def __init__(self, sysname, config=None):
        self.sysname = sysname
        self.config = config
        self.dir = DirectoryStandalone(sysname=self.sysname, config=config)

    def create_core_datastores(self):
        """
        Main entry point into creating core datastores
        """
        ds = CouchDataStore(config=self.config, scope=self.sysname)
        datastores = ['resources','directory']
        for local_dsn in datastores:
            if not ds.exists_datastore(local_dsn):
                ds.create_datastore(local_dsn)
                # NOTE: Views are created by containers' DatastoreManager

    def store_config(self, system_cfg):
        """
        Main entry point into storing system config
        """
        print "Storing system config in datastore..."
        de = self.dir.lookup(self.DIR_CONFIG_PATH + "/CFG")
        if de:
            print "store_interfaces: WARN: Config already exists. Overwrite"
        self.dir.register(self.DIR_CONFIG_PATH, "CFG", **system_cfg.copy())

    def store_interfaces(self, object_definition_file=None,
                         service_definition_file=None, store_bulk=True, idempotent=False):
        """
        Main entry point into storing interfaces
        """
        self.object_definition_file = object_definition_file
        self.service_definition_file = service_definition_file
        self.store_bulk = store_bulk
        self.idempotent = idempotent
        self.bulk_entries = {}
        self.serial_num = 1

        if self.service_definition_file:
            if os.path.exists(self.service_definition_file):
                self.load_from_files(self.DIR_SERVICEDEF_PATH,
                    [self.service_definition_file],
                    self.get_service_file_content)
            else:
                print "store_interfaces: Error couldn't find the file path\n"
        elif self.object_definition_file:
            if os.path.exists(self.object_definition_file):
                self.load_from_files(self.DIR_OBJECTTYPES_PATH,
                    [self.object_definition_file],
                    self.get_object_file_content())
            else:
                print "store_interfaces: Error couldn't find the file path\n"
        else:
            if self.idempotent:
                de = self.dir.lookup(self.DIR_SERVICEDEF_PATH)
                if de is not None:
                    #print "store_interfaces: Interfaces already stored. Ignoring"
                    return
            # load all files
            self.store_config_files()
            self.store_object_interfaces()
            self.store_service_interfaces()

        if self.store_bulk:
            self._register_bulk()

    def store_config_files(self):
        if not self.store_bulk:
            print "\nStoring system res files in datastore..."
        resource_filenames = list_files_recursive('res/config', '*.yml')
        self.load_from_files(self.DIR_RESFILES_PATH, resource_filenames,
            self.get_config_file_content)

    def store_object_interfaces(self):
        if not self.store_bulk:
            print "\nStoring object interfaces in datastore..."
        data_yaml_filenames = list_files_recursive('obj/data', '*.yml',
            ['ion.yml', 'resource.yml',
             'shared.yml'])
        self.load_from_files(self.DIR_OBJECTTYPES_PATH, data_yaml_filenames,
            self.get_object_file_content)

    def store_service_interfaces(self):
        service_yaml_filenames = list_files_recursive('obj/services', '*.yml')
        if not self.store_bulk:
            print "\nStoring service interfaces in datastore..."
        self.load_from_files(self.DIR_SERVICEDEF_PATH,
            service_yaml_filenames,
            self.get_service_file_content)

    def display_header(self):
        if not self.store_bulk:
            print "--------------------------------------------------------------"
            print "Key".ljust(40), "Filename".ljust(60)
            print "--------------------------------------------------------------"

    def load_from_files(self, path, filenames, get_file_content_method):
        '''
        Gets file content and load it to datastore
        '''
        self.display_header()
        for file_path in filenames:
            content = get_file_content_method(file_path)
            for key in content.keys():
                if not self.store_bulk:
                    print key.ljust(40), file_path.ljust(60)
                self.store_in_datastore(path, key, content[key], file_path)

    def store_in_datastore(self, path, key, content, filename):
        '''
        Store in datastore
        '''
        if self.store_bulk:
            if ("/", path[1:]) not in self.bulk_entries:
                self.bulk_entries[("/", path[1:])] = {}

            dir_key = (path, key)
            if dir_key in self.bulk_entries:
                print '\033[91m' "\nLoad Configuration Error!!! Multiple definitions found:\n"
                print '\033[92m' "Filename:", filename
                print '\033[91m', content
                print '\033[92m' "\nPrevious definition:"
                print '\033[91m', self.bulk_entries[dir_key]['definition']
                print '\033[0m'
                exit()

            self.bulk_entries[dir_key] = dict(file_path=filename, definition=content, ordinal=self.serial_num)
            self.serial_num += 1
        else:
            if not self.dir.lookup(path):
                self.dir.register("/", path[1:])

            new_entry = self.dir.register(path, key, file_path=filename, definition=content, ordinal=self.serial_num)
            self.serial_num += 1
            if new_entry is not None:
                print '\033[91m' "\nLoad Configuration Error!!! Multiple definitions found:\n"
                print '\033[92m' "Filename:", filename
                print '\033[91m', content
                print '\033[92m' "\nPrevious definition:"
                print '\033[91m', new_entry['attributes']['definition']
                print '\033[0m'
                exit()

            new_entry = self.dir.lookup(path + '/' + key)
            if content != new_entry['definition']:
                print '\n\nError adding: ' + key + ' to the directory'
                exit()

    def _register_bulk(self):
        print "store_interfaces: Storing %s interfaces in datastore (bulk)..." % len(self.bulk_entries)
        entries = [(path, key, attrs) for ((path, key), attrs) in self.bulk_entries.iteritems()]
        res = self.dir.register_mult(entries)
        print "store_interfaces: Storing interfaces successful"

    def get_config_file_content(self, file_path):
        '''
            Read file content from res/config and returns dict with key
            equals to filename and value equals to file content
        '''
        with open(file_path, 'r') as f:
            file_content_str = f.read()
        objs = {}
        objs[os.path.basename(file_path)] = file_content_str

        return objs

    def get_object_file_content(self, file_path):
        '''
            Return dict with key equal to classname and value equal to text
            representation of class definition
        '''
        file_content_str = ""
        objs = OrderedDict()
        class_content = ''

        # Open and read data model definition file
        with open(file_path, 'r') as f:
            file_content_str = f.read()

        first_time = True
        for line in file_content_str.split('\n'):
            #if len(line) == 0:
            #    continue
            #if line == "---":
            #    continue
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

        #print "******", objs
        return objs

    def get_service_file_content(self, file_path):
        file_content_str = ""
        key = ""
        objs = {}
        with open(file_path, 'r') as f:
            file_content_str = f.read()
        for line in file_content_str.split('\n'):
            if line[:5] == "name:":
                key = line.split()[1]
                objs[key] = file_content_str

        if not objs:
            print "\n\n=====ERROR===== Can't find object name for: ", file_path

        #print "******", objs
        return objs

def recursive_strip(scan_obj):
    """
    HACK HACK HACK
    """
    if type(scan_obj) is dict:
        for key, value in scan_obj.iteritems():
            if type(value) not in (str, int, float, bool, dict, list, None):
                scan_obj[key] = str(value)
            if type(value) is dict:
                recursive_strip(value)

def _bootstrap_object_defs(directory):
    from pyon.core.object import IonObjectBase
    from interface import objects

    # @TODO: This should use the same code as the load_configuration tool
    delist = []
    for cname, cobj in inspect.getmembers(objects, inspect.isclass):
        if issubclass(cobj, IonObjectBase) and cobj != IonObjectBase:
            parentlist = [parent.__name__ for parent in cobj.__mro__ if parent.__name__ not in ['IonObjectBase','object']]
            delist.append(("/ObjectTypes", cname, dict(schema=recursive_strip(cobj._schema), extends=parentlist)))
    directory.register_mult(delist)

def _bootstrap_service_defs(directory):
    from pyon.service.service import IonServiceRegistry

    # @TODO: This should use the same code as the load_configuration tool
    # At this time importing everything is THE KILLER
    service_registry = IonServiceRegistry()
    service_registry.load_service_mods('interface/services')
    service_registry.build_service_map()

    svc_list = []
    for svcname, svc in service_registry.services.iteritems():
        svc_list.append(("/ServiceInterfaces", svcname, {}))
    directory.register_mult(svc_list)
