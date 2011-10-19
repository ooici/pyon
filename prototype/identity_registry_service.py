#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from collections import OrderedDict

from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound
from pyon.util.log import log

from interface.services.iidentity_registry_service import BaseIdentityRegistryService

class IdentityRegistryService(BaseIdentityRegistryService):

    def create_user(self, name='', subjects='', email='', phone='', variables=[OrderedDict([('name', ''), ('value', '')])]):
        log.debug("In create_user")
        log.debug("name: %s" % name)
        log.debug("email: %s" % email)
        log.debug("phone: %s" % phone)
        log.debug("subjects: %s" % subjects)
        log.debug("variables: %s" % str(variables))
        try:
            res = self.clients.datastore.find("UserInfo", "name", name)
            log.info("User already exists. Raising exception")
            # TODO
        except NotFound:
            log.debug("New user")

        # Create user info entry
        userinfo = {}
        userinfo["name"] = name
        userinfo["roles"] = ""
        userinfo["subjects"] = subjects
        userinfo["email"] = email
        userinfo["phone"] = phone
        userinfo["variables"] = variables
        userinfo_obj = IonObject("UserInfo", userinfo)
        userinfo_create_tuple = self.clients.datastore.create(userinfo_obj)
        user_id = userinfo_create_tuple[0]
        userinfo_obj._id = user_id

        log.debug("Created user. User info: %s" % str(userinfo))

        return userinfo_obj

    def update_user(self, name='', subjects='', email='', phone='', variables=[OrderedDict([('name', ''), ('value', '')])]):
        log.debug("In update_user")
        log.debug("name: %s" % name)
        log.debug("email: %s" % email)
        log.debug("phone: %s" % phone)
        log.debug("subjects: %s" % subjects)
        log.debug("variables: %s" % str(variables))
        try:
            userinfo = self.clients.datastore.find("UserInfo", "name", name)[0]
            log.debug("User found")

            # Update user info entry
            userinfo["Name"] = name
            userinfo["email"] = email
            userinfo["phone"] = phone
            userinfo["subjects"] = subjects
            userinfo["variables"] = variables
            userinfo_obj = IonObject("UserInfo", userinfo)
            userinfo_update_tuple = self.clients.datastore.update(userinfo_obj)

            log.debug("Updated user %s." % name)

            return userinfoObj
        except NotFound:
            log.info("User not found. Raising exception")
            # TODO

    def remove_user(self, name='', email=''):
        log.debug("In remove_user")
        log.debug("name: %s" % name)
        log.debug("email: %s" % email)
        try:
            obj = self.clients.datastore.find("UserInfo", "name", name)[0]
            log.debug("User found")
            self.clients.datastore.delete(obj)
        except NotFound:
            log.info("User not found. Raising exception")
            # TODO

    def find_user_by_id(self, id=''):
        log.debug("In find_user_by_id")
        log.debug("id: %s" % id)
        try:
            userinfo = self.clients.datastore.read(id)[0]
            log.debug("User found: %s" % str(userinfo))
            return userinfo
        except NotFound as ex:
            log.info("User not found. Re-raising exception")
            raise ex

    def find_user_by_name(self, name=''):
        log.debug("In find_user_by_name")
        log.debug("name: %s" % name)
        try:
            userinfo = self.clients.datastore.find("UserInfo", "name", name)[0]
            log.debug("User found: %s" % str(userinfo))
            return userinfo
        except NotFound as ex:
            log.info("User not found. Re-raising exception")
            raise ex

    def find_user_by_subject(self, subject=''):
        log.debug("In find_user_by_subject")
        log.debug("subject: %s" % subject)
        try:
            userinfo = self.clients.datastore.find("UserInfo", "subjects", subject)[0]
            log.debug("User found: %s" % str(userinfo))
            return userinfo
        except NotFound as ex:
            log.info("User not found. Re-raising exception")
            raise ex

    def add_cilogon_subject_to_user(self, name='', subject=''):
        pass

    def update_cilogon_subject_for_user(self, name='', old_subject='', new_subject=''):
        pass

    def remove_cilogon_subject_from_user(self, name='', subject=''):
        pass

    def get_user_roles(self, name=''):
        pass

    def set_user_role(self, name='', role=''):
        pass

    def unset_user_role(self, name='', role=''):
        pass


  