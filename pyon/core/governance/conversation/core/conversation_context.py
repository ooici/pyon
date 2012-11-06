#!/usr/bin/env python

__author__ = 'Rumyana Neykova'
__license__ = 'Apache 2.0'


class ConversationContext(object):
    def __init__(self, builder, conv_id, principals, op_mapping):
        self.builder = builder
        self.builder.main_fsm.fsm.reset()
        self.unset_roles = iter(self.builder.roles)
        self.builder.main_fsm.fsm.instantiate_generics(op_mapping)
        # principal -> role
        self.role_mapper = {}
        self.conv_id = conv_id
        #[self.set_default_role_mapping(principal) for principal in principals]

    def get_fsm(self):
        return self.builder.main_fsm.fsm

    def get_conversation_id(self):
        return self.conv_id

    def get_next_unset_role(self):
        try:
            return  self.unset_roles.next()
        except StopIteration:
            return 'Unknown'

    def set_role_mapping(self, role, principal):
        self.role_mapper[principal] =  role

    def set_default_role_mapping(self, principal):
        if not(principal in self.role_mapper):
            next_role = self.get_next_unset_role()
            self.set_role_mapping(next_role, principal)

    def get_role_by_principal(self, principal):
        self.set_default_role_mapping(principal)
        return self.role_mapper[principal]