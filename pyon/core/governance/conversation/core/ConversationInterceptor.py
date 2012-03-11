from ConversationMonitor import ConversationMonitor
from messaging.ExchangeGateway import ExchangeGateway
from core.AMQPConversationMessageAdapter import AMQPConversationMessageAdapter
from threading import Thread
from test import *
import time

class ConversationInterceptor(object):
    DEFAULT_EXCHANGE = '' 
    RESEND = 'RESEND'
    def __init__(self, participant):
        self.participant = participant
        self.conversation_monitor = ConversationMonitor()
        self.message_adapter = AMQPConversationMessageAdapter()
        self.invitations = {}
        self.gateway = ExchangeGateway()
        self.monitor_enabled = True
        
    def start(self):
        # received all invitations for the participant and forward them to the participant queue
        self.gateway.start_forwarding(self.DEFAULT_EXCHANGE, #source_exchange  
                                              self.participant,      #destination_exchange  
                                              self.participant,      #source_binding
                                              self.on_incoming_invitation, #interceptor  
                                              self.participant)     #source_queue_name
        self.gateway.consume(self.participant)
        self._handle_accept_invitation()

    def on_incoming_invitation(self, ch, method, properties, body):
        # in invitation
        print "on_incoming_invitation: %s" %(self.participant)
        invitation = self.message_adapter.to_invitation_msg(body) 
        if self.monitor_enabled:
            self.conversation_monitor.on_incoming_invitations(invitation)
        self.invitations.setdefault(self.participant, invitation)         
        # callback_queue
        properties.reply_to = self.participant
        return (self.RESEND, method, properties, True, None)
                                        
    def _handle_accept_invitation(self):
        print "_handle_accept_invitation: exchange:%s" %self.participant
        invitation = self.invitations.get(self.participant, )
        if self.monitor_enabled:
            f = open('/homes/rn710/benchmarks/Monitor_check.txt', 'a')
            t = time.time()
            self.conversation_monitor.on_accept_invitation(invitation)
            full_msg = "init:%s\n"%(time.time() - t)
            f.write(full_msg)
            f.flush()
            f.close()
        monitor_queue = 'monitor-%s' %(self.participant)
        self.gateway.start_forwarding(self.participant, 
                                               invitation.cid, 
                                               "*.%s.*" %(invitation.role), 
                                               self.on_outgoing_msg, 
                                               monitor_queue)
        
        self.gateway.start_forwarding(invitation.cid, 
                                               self.participant, 
                                               "*.*.%s" %(invitation.role), 
                                               self.on_incoming_msg, 
                                               monitor_queue)
        self.gateway.consume(monitor_queue)
        
    def on_outgoing_msg(self, ch, method, properties, body):
        result = self.RESEND
        conv_msg = self.message_adapter.to_conversation_msg(body)
        if conv_msg.label =='END':
            self.gateway.stop_forwarding() 
            return ('DO_NOT_RESEND', method, properties, False, None)
        elif self.monitor_enabled:
                f = open('/homes/rn710/benchmarks/Monitor_check.txt', 'a')
                t = time.time()
                if self.conversation_monitor.check_outgoing_msg(conv_msg):
                    result = self.RESEND
                else: result = 'ERROR'
                full_msg = "msg:%s\n"%(time.time() - t)
                f.write(full_msg)
                f.flush()
                f.close()
        return (result, method, properties, False, None)
    
    
    def on_incoming_msg(self, ch, method, properties, body):
        result = self.RESEND
        conv_msg = self.message_adapter.to_conversation_msg(body)
        if (conv_msg.label =='END'): 
            self.gateway.stop_forwarding()
            return ('DO_NOT_RESEND', method, properties, False, None)
            #conv_msg.label =='END': self.gateway.stop_consume()
        elif self.monitor_enabled:
                    f = open('/homes/rn710/benchmarks/Monitor_check.txt', 'a')
                    t = time.time()
                    if self.conversation_monitor.check_incoming_msg(conv_msg):
                        result  =  self.RESEND
                    else: result = 'ERROR'
                    #print time.time() - t
                    full_msg = "msg:%s \n"%(time.time() - t)
                    f.write(full_msg)
                    f.flush()
                    f.close()
        return (result, method, properties, False, None)