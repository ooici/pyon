#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from anode.core.bootstrap import AnodeObject
from anode.datastore.datastore import NotFoundError
from anode.util.log import log

from interface.services.iidentity_registry_service import BaseIdentityRegistryService

class IdentityRegistryService(BaseIdentityRegistryService):

    def __init__(self, configParams={}):
        log.debug("In __init__")
        pass

    def create_user(self, phone='', variables=[{'name': '', 'value': ''}], subjects='', name='', email=''):
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
        except NotFoundError:
            log.debug("New user")

        # Create user info entry
        userinfo = {}
        userinfo["Name"] = name
        userinfo["email"] = email
        userinfo["phone"] = phone
        userinfo["subjects"] = subjects
        userinfo["variables"] = variables
        userinfoObj = AnodeObject("UserInfo", userinfo)
        userinfoCreateTuple = self.clients.datastore.create(userinfoObj)
        userId = userinfoCreateTuple[0]

        log.debug("Created user %s.  User id is %s" % (name, userId))

        return userinfoObj

    def update_user(self, phone='', variables=[{'name': '', 'value': ''}], subjects='', name='', email=''):
        log.debug("In update_user")
        log.debug("name: %s" % name)
        log.debug("email: %s" % email)
        log.debug("phone: %s" % phone)
        log.debug("subjects: %s" % subjects)
        log.debug("variables: %s" % str(variables))
        try:
            userinfo = self.clients.datastore.find("UserInfo", "name", name)
            log.debug("User found")

            # Update user info entry
            userinfo["Name"] = name
            userinfo["email"] = email
            userinfo["phone"] = phone
            userinfo["subjects"] = subjects
            userinfo["variables"] = variables
            userinfoObj = AnodeObject("UserInfo", userinfo)
            userinfoUpdateTuple = self.clients.datastore.update(userinfoObj)

            log.debug("Updated user %s." % name)

            return userinfoObj
        except NotFoundError:
            log.info("User not found. Raising exception")
            # TODO

    def remove_user(self, name='', email=''):
        log.debug("In remove_user")
        log.debug("name: %s" % name)
        log.debug("email: %s" % email)
        try:
            obj = self.clients.datastore.find("UserInfo", "name", name)
            log.debug("User found")
            self.clients.datastore.delete(obj)
        except NotFoundError:
            log.info("User not found. Raising exception")
            # TODO

    def find_user_by_id(self, id=''):
        log.debug("In find_user_by_id")
        log.debug("id: %s" % id)
        try:
            userinfo = self.clients.datastore.read(id)
            log.debug("User found: %s" % str(userinfo))
            return userinfo
        except NotFoundError:
            log.info("User not found. Raising exception")
            # TODO

    def find_user_by_name(self, name=''):
        log.debug("In find_user_by_name")
        log.debug("name: %s" % name)
        try:
            userinfo = self.clients.datastore.find("UserInfo", "name", name)
            log.debug("User found: %s" % str(userinfo))
            return userinfo
        except NotFoundError:
            log.info("User not found. Raising exception")
            # TODO

    def find_user_by_subject(self, subject=''):
        log.debug("In find_user_by_subject")
        log.debug("subject: %s" % subject)
        try:
            userinfo = self.clients.datastore.find("UserInfo", "subjects", subject)
            log.debug("User found: %s" % str(userinfo))
            return userinfo
        except NotFoundError:
            log.info("User not found. Raising exception")
            # TODO

    def add_cilogon_subject_to_user(self, name='', subject=''):
        pass

    def update_cilogon_subject_for_user(self, name='', oldSubject='', newSubject=''):
        pass

    def remove_cilogon_subject_from_user(self, name='', subject=''):
        pass

    def get_user_roles(self, name=''):
        pass

    def set_user_role(self, name='', role=''):
        pass

    def unset_user_role(self, name='', role=''):
        pass


  