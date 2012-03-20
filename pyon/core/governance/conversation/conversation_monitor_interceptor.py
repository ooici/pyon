#!/usr/bin/env python

__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

import os
from pyon.core.governance.governance_interceptor import BaseInternalGovernanceInterceptor
from pyon.util.log import log
from parsing.base_parser import ANTLRScribbleParser
from core.transition import TransitionFactory
from core.local_type import LocalType
from core.fsm import FSM, ExceptionFSM
from core.conversation_context import ConversationContext

# The current interceptor can monitor only one conversation at a time for a given principal
class ConversationMonitorInterceptor(BaseInternalGovernanceInterceptor):
    def __init__(self):
        self.spec_path = os.path.normpath("%s/../specs/" %__file__)
        self._initialize_conversation_for_monitoring()
        #map principal to conversation_context
        self.conversation_context = {}

    def _initialize_conversation_for_monitoring(self):
        self.conversations_for_monitoring = {'bank':{'buy_bonds':'bank/local/BuyBonds_Bank.srt',
                                                     'new_account':'bank/local/NewAccount_Bank.srt'},
                                             'trade':{'exercise':'bank/local/BuyBonds_Trade.srt'}
                                            }


    def outgoing(self, invocation):
        if invocation.args.has_key('process'):
            log.debug("ConversationMonitorInterceptor.outgoing: %s", invocation.get_arg_value('process',invocation))
        else:
            log.debug("ConversationMonitorInterceptor.outgoing: %s", invocation)

        self_principal = self._get_process(invocation)

        if self_principal:
            target_principal = self._get_receiver(invocation)
            op_type = LocalType.SEND;
            self._check(invocation, op_type, self_principal, target_principal)
        else: self._report_error(invocation, 'Message cannot be checked. There is no associated process')
        return invocation

    def incoming(self, invocation):
        if invocation.args.has_key('process'):
            log.debug("ConversationMonitorInterceptor.incoming: %s", invocation.get_arg_value('process',invocation))
        else:
            log.debug("ConversationMonitorInterceptor.incoming: %s", invocation)

        self_principal = self._get_process(invocation)

        if self_principal:
            target_principal = self._get_sender(invocation)
            target_principal_queue = self._get_sender_queue(invocation)
            op_type = LocalType.RESV;

            if target_principal=='Unknown':
                target_principal = target_principal_queue
                self._check(invocation, op_type, self_principal, target_principal)
            else: self._check(invocation, op_type, self_principal, target_principal, target_principal_queue)

        else: self._report_error(invocation, 'Message cannot be checked. There is no associated process')

        return invocation

    def _initialize_conversation_context(self, cid, role_spec, principals):
        try:
            parser = ANTLRScribbleParser()
            res = parser.parse(os.path.join(self.spec_path,role_spec))
            builder = parser.walk(res)
            return ConversationContext(builder, cid, principals)
        except Exception as inst:
            log.debug("ConversationMonitorInterceptor._initialize_conversation_context: %s",
                "Conversation context cannot be created")

    def  _check(self, invocation, op_type, self_principal, target_principal, target_principal_queue = None):

        operation = invocation.get_header_value('op', '')
        cid = invocation.get_header_value('conv-id', 0)
        conv_seq = invocation.get_header_value('conv-seq', 0)
        conversation_key = self._get_conversation_context_key(self_principal,  invocation)

        # INITIALIZE FSM
        if ((conv_seq == 1 and self._should_be_monitored(invocation, self_principal.name, operation)) and
            not((conversation_key in self.conversation_context))):

            role_spec = self._get_protocol_spec(self_principal.name, operation)
            if not role_spec:
                self._report_error(invocation, 'No specification given. Message cannot be monitored: %s')
            else:
                conversation_context = self._initialize_conversation_context(cid, role_spec,
                                                                        [self_principal, target_principal])
                if conversation_context: self.conversation_context[conversation_key] = conversation_context

        # CHECK
        if (conversation_key in self.conversation_context):
            conversation_context = self.conversation_context[conversation_key]

            target_role = conversation_context.get_role_by_principal(target_principal)
            if target_principal_queue and target_role:
                # reply-to queue should be mapped, because the queue will be the receiver when the response is send.
                conversation_context.set_role_mapping(target_role, target_principal_queue)
            fsm = conversation_context.get_fsm()
            transition = TransitionFactory.create(op_type, operation, target_role)

            #Check the message by running the fsm.
            (msg_correct, error)= self._is_msg_correct(invocation, fsm, transition)
            if not msg_correct:
                self._report_error(invocation, error)

            # Stop monitoring if msg is wrong or this is the response of the request that had started the conversation
            if (not msg_correct) or ((conv_seq != 1) and (conversation_context.get_conversation_id() == cid)):
                self.conversation_context.pop(conversation_key)

    def _is_msg_correct(self, invocation, fsm, transition):
        try:
            fsm.process(transition)
            return (True,None)
        except ExceptionFSM as e:
            return (False, e.value)

    def _report_error(self, invocation, error):
        invocation.message_annotations.setdefault('conversation', error)
        log.debug("ConversationMonitorInterceptor.incoming error: %s", error)

    def _get_conversation_context_key(self, principal, invocation):
        initiating_conv_id = invocation.get_header_value('initiating-conv-id', None)
        # Note, one principal can play only one role, but in general the key should be: (conv_id, prinicpla.od, role)
        key = (initiating_conv_id, principal.id, principal.name)
        return key

    def _should_be_monitored(self, invocation, principal_name, operation):
        initiating_conv_id = invocation.get_header_value('initiating-conv-id', None)
        return   ((principal_name in self.conversations_for_monitoring) and \
                  (operation in self.conversations_for_monitoring[principal_name])) and  \
                   initiating_conv_id

    def _get_protocol_spec(self, role, operation ):
        return self.conversations_for_monitoring[role][operation]

    def _get_sender_queue(self, invocation):
        sender_queue = invocation.get_header_value('reply-to', 'todo')
        if (sender_queue == 'todo'):
            return None
        else:
            index = sender_queue.find('amq')
            if (index != -1): sender_queue = sender_queue[index:]
            return sender_queue

    def _get_sender(self, invocation):
        sender_type = invocation.get_header_value('sender-type', 'Unknown')

        if sender_type == 'service':
            sender_header = invocation.get_header_value('sender-service', 'Unknown')
            sender = invocation.get_service_name(sender_header)
        else:
            sender = invocation.get_header_value('sender', 'Unknown')
        return sender

    def _get_process(self, invocation):
        value = invocation.args['process'] if 'process' in invocation.args else None
        return value

    def _get_receiver(self, invocation):
        receiver_header = invocation.get_header_value('receiver', 'Unknown')
        receiver = invocation.get_service_name(receiver_header)
        return receiver

