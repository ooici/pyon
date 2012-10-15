#!/usr/bin/env python
from __builtin__ import classmethod

__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

import os
from pyon.core.governance.governance_interceptor import BaseInternalGovernanceInterceptor
from pyon.util.log import log
from pyon.net import conversation
from pyon.net.conversation import MSG_TYPE_MASKS
from parsing.base_parser import ANTLRScribbleParser
from core.transition import TransitionFactory
from core.local_type import LocalType
from core.fsm import FSM, ExceptionFSM
from core.conversation_context import ConversationContext

class ConversationProvider(object):
    @classmethod
    def get_protocol_mapping(cls, op):
        return {'request': op}

# The current interceptor can monitor only one conversation at a time for a given principal
class ConversationMonitorInterceptor(BaseInternalGovernanceInterceptor):
    def __init__(self):
        self.spec_path = os.path.normpath("%s/../specs/" %__file__)
        self._initialize_conversation_for_monitoring()
        #map principal to conversation_context
        self.conversation_context = {}

    def _initialize_conversation_for_monitoring(self):
        #self.conversations_for_monitoring = {'bank':{'buy_bonds':'bank/local/BuyBonds_Bank.srt',
        #                                             'new_account':'bank/local/NewAccount_Bank.srt'},
        #                                     'trade':{'exercise':'bank/local/BuyBonds_Trade.srt'}
        #                                    }

        self.conversations_for_monitoring = {'requester': 'rpc_generic/local/rpc_requester.srt',
                                             'provider': 'rpc_generic/local/rpc_provider.srt'}


    def outgoing(self, invocation):
        if invocation.args.has_key('process'):
            log.debug("ConversationMonitorInterceptor.outgoing: %s", invocation.get_arg_value('process',invocation))
        else:
            log.debug("ConversationMonitorInterceptor.outgoing: %s", invocation)

        self_principal = invocation.headers.get('sender-role', None)
        target_principal = invocation.headers.get('receiver-role', None)
        op_type = LocalType.SEND;
        log.debug("ConversationMonitorInterceptor.outgoing: %s", invocation.get_arg_value('process', invocation))

        if self_principal and target_principal:
        #    target_principal = self._get_receiver(invocation)
        #    op_type = LocalType.SEND;
            self._check(invocation, op_type, self_principal, target_principal)
        else: self._report_error(invocation, 'Message cannot be checked. There is no associated process')
        return invocation

    def incoming(self, invocation):
        print 'I am in conversation interceptor!!!'
        if invocation.args.has_key('process'):
            log.debug("ConversationMonitorInterceptor.incoming: %s", invocation.get_arg_value('process',invocation))
        else:
            log.debug("ConversationMonitorInterceptor.incoming: %s", invocation)

        self_principal = invocation.headers.get('receiver-role', None)
        target_principal = invocation.headers.get('sender-role', None)
        op_type = LocalType.RESV;
        if self_principal and target_principal:
        #if self_principal:
        #    target_principal = self._get_sender(invocation)
        #    target_principal_queue = self._get_sender_queue(invocation)
        #    op_type = LocalType.RESV;
        #
        #    if target_principal=='Unknown':
        #        target_principal = target_principal_queue
        #        self._check(invocation, op_type, self_principal, target_principal)
        #    else: self._check(invocation, op_type, self_principal, target_principal, target_principal_queue)

            self._check(invocation, op_type, self_principal, target_principal)
        else: self._report_error(invocation, 'Message cannot be checked. There is no associated process')

        return invocation

    def _initialize_conversation_context(self, cid, role_spec, principals, op):
        #try:
        parser = ANTLRScribbleParser()
        res = parser.parse(os.path.join(self.spec_path,role_spec))
        builder = parser.walk(res)
        mapping = ConversationProvider.get_protocol_mapping(op)
        return ConversationContext(builder, cid, principals, mapping)
        #except Exception as inst:
        #    log.debug("ConversationMonitorInterceptor._initialize_conversation_context: %s",
        #        "Conversation context cannot be created")
        #    raise  inst

    def _get_control_conv_msg(self, invocation):
            return invocation.get_header_value('conv-msg-type') & MSG_TYPE_MASKS.CONTROL

    def _get_in_session_msg_type(self, invocation):
        return invocation.get_header_value('conv-msg-type') & MSG_TYPE_MASKS.IN_SESSION

    def  _check(self, invocation, op_type, self_principal, target_principal):
        print 'In check'
        operation = invocation.get_header_value('op', '')
        cid = invocation.get_header_value('conv-id', 0)
        conv_seq = invocation.get_header_value('conv-seq', 0)
        conversation_key = self._get_conversation_context_key(self_principal,  invocation)

        # INITIALIZE FSM
        if ((conv_seq == 1 and self._should_be_monitored(invocation, self_principal, operation)) and
            not((conversation_key in self.conversation_context))):

            role_spec = self._get_protocol_spec(self_principal, operation)
            print 'role_spec', role_spec
            if not role_spec:
                self._report_error(invocation, 'No specification given. Message cannot be monitored: %s')
            else:
                conversation_context = self._initialize_conversation_context(cid, role_spec,
                                                                        [self_principal, target_principal],
                                                                        operation)
                if conversation_context: self.conversation_context[conversation_key] = conversation_context
                print 'conversation_context', conversation_context

        # CHECK
        if (conversation_key in self.conversation_context):
            conversation_context = self.conversation_context[conversation_key]

            #target_role = conversation_context.get_role_by_principal(target_principal)
            target_role = target_principal
            #if target_principal_queue and target_role:
                #conversation_context.set_role_mapping(target_role, target_principal_queue)
            fsm = conversation_context.get_fsm()

            control_conv_msg_type = self._get_control_conv_msg(invocation)

            print 'Are they equeal:%s, %s'%(control_conv_msg_type, (control_conv_msg_type == conversation.MSG_TYPE.ACCEPT))
            if (control_conv_msg_type == conversation.MSG_TYPE.ACCEPT):
                transition = TransitionFactory.create(op_type, 'accept', target_role)
                (msg_correct, error)= self._is_msg_correct(invocation, fsm, transition)
                if not msg_correct:
                    self._report_error(invocation, error)
                    return

            transition = TransitionFactory.create(op_type, operation, target_role)

        #Check the message by running the fsm.
            (msg_correct, error)= self._is_msg_correct(invocation, fsm, transition)
            if not msg_correct:
                self._report_error(invocation, error)

            # Stop monitoring if msg is wrong or this is the response of the request that had started the conversation
            if (not msg_correct) or ((conv_seq != 1) and (conversation_context.get_conversation_id() == cid)):
                self.conversation_context.pop(conversation_key)

    def _is_msg_correct(self, invocation, fsm, transition):
        details = ''
        try:
            fsm.process(transition)
            status = 'CORRECT'
            return (True, None)
        except ExceptionFSM as e:
            status = 'WRONG'
            details = e.value
            return (False, e.value)
        finally:
            log.info("""\n
        ----------------Checking message:-----------------------------------------------
        Message is: =%s  \n
        Status: %s  \n
        Details: %s  \n
        --------------------------------------------------------------------------------
            """, invocation.headers, status, details)

    def _report_error(self, invocation, error):
        cur_label = invocation.get_header_value('op', None)
        if not cur_label: cur_label = invocation.message
        msg = 'Conversation error for message %s \n  Error: %s' %(cur_label, error)
        invocation.message_annotations.setdefault(msg)
        log.debug("ConversationMonitorInterceptor error: %s", msg)

    def _get_conversation_context_key(self, principal, invocation):
        #initiating_conv_id = invocation.get_header_value('initiating-conv-id', None)
        initiating_conv_id = invocation.get_header_value('conv-id', None)
        # Note, one principal can play only one role, but in general the key should be: (conv_id, prinicpla.od, role)
        key = (initiating_conv_id, principal)
        return key

    def _should_be_monitored(self, invocation, principal_name, operation):
        #initiating_conv_id = invocation.get_header_value('initiating-conv-id', None)
        #return   ((principal_name in self.conversations_for_monitoring) and \
        #          (operation in self.conversations_for_monitoring[principal_name])) and  \
        #           initiating_conv_id
        return True

    def _get_protocol_spec(self, role, operation ):
        print 'The role is:', role
        return self.conversations_for_monitoring[role]

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

    def _get_receiver(self, invocation):
        receiver_header = invocation.get_header_value('receiver', 'Unknown')
        receiver = invocation.get_service_name(receiver_header)
        return receiver