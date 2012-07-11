import uuid
import collections
import time
from gevent.timeout import Timeout
from pyon.core import bootstrap, exception
from gevent import coros
from pyon.core.exception import IonException
from pyon.util.log import log
from pyon.net.transport import NameTrio, BaseTransport
from pyon.net.channel import BidirChannel, ListenChannel, ChannelClosedError, ChannelShutdownMessage
from pyon.core.interceptor.interceptor import Invocation, process_interceptors
from gevent import queue as gqueue
from gevent.event import AsyncResult
from pyon.util.async import spawn, switch
#@TODO: Fix this, the interceptors should be local, Conversation should not import endpoint
from endpoint import interceptors, log_message
#@TODO: RPC specific import, should be removed
from pyon.core.bootstrap import CFG

#@TODO: Add log.debug to all methods, can we do geenral on class level, except for typing it in every method?
#@TODO: How to manage **kwargs???
#@TODO: Add @param and @returns to all methods
#@TODO: Queuest should be auto deleted

class ConversationError(IonException):
    pass


class PrincipalError(IonException):
    pass


def enum(**enums):
    return type('Enum', (), enums)

def get_control_msg_type(header):
    if (header.has_key('conv-msg-type')):
        return header['conv-msg-type'] & MSG_TYPE_MASKS.CONTROL
    else: raise ConversationError('conv-msg-type in not set in the message header')

def get_in_session_msg_type(header):
    if (header.has_key('conv-msg-type')):
        return header['conv-msg-type'] & MSG_TYPE_MASKS.IN_SESSION
    else: raise ConversationError('conv-msg-type in not set in the message header')

# @TODO: Do we need CLOSE ???
MSG_TYPE = enum(TRANSMIT = 1, INVITE=8, ACCEPT=16, REJECT = 24)
MSG_TYPE_MASKS = enum(IN_SESSION = 7, CONTROL= 56)


class Conversation(object):
    conv_id_counter = 0
    _lock = coros.RLock()       # @TODO: is this safe?
    _conv_id_root = None

    def __init__(self, protocol, cid = None):
        self._conv_table = {}
        self.protocol = protocol
        if cid: self._conv_id = cid
        else:   self._conv_id = self._build_conv_id()

    @property
    def protocol(self):
         return self._protocol

    @protocol.setter
    def protocol(self, value):
         self._protocol = value

    @property
    def id(self):
        return self._id

    @id.setter
    def protocol(self, value):
        self._id = value

    def __getitem__(self, to_role):
        print "In._get_from_conv_table"
        self._conv_table.setdefault(to_role, AsyncResult())
        if isinstance(self._conv_table[to_role], AsyncResult):
            # @TODO. Need timeout for the AsyncResult
            print "Wait on the Async Result"
            to_role_addr = self._conv_table[to_role].get()
            print "get the Async Result, value is:%s" %to_role_addr
            self._conv_table[to_role] = to_role_addr
        return self._conv_table[to_role]

    def __setitem__(self, to_role, to_role_addr):
        print 'Conversation._add_to_conv_table: to_role:%s, to_role_addr:%s' %(to_role, to_role_addr)
        if to_role in self._conv_table and isinstance(self._conv_table[to_role], AsyncResult):
            self._conv_table[to_role].set(to_role_addr)
        else: self._conv_table[to_role] = to_role_addr

    def has_role(self, role):
        return role in self._conv_table

    # TODO: Why we need the counter here?. This is a copy from endpoint.py, it should be changed
    def _build_conv_id(self):
        """
        Builds a unique conversation id based on the container name.
        """
        with Conversation._lock:
            Conversation.conv_id_counter += 1

            if not Conversation._conv_id_root:
                # set default to use uuid-4, similar to what we'd get out of the container id anyway
                Conversation._conv_id_root = str(uuid.uuid4())[0:6]

                # try to get the real one from the container, but do it safely
                #@ TODO: tooo OOI specific, move it to OOIConversation derived class
                try:
                    from pyon.container.cc import Container
                    if Container.instance and Container.instance.id:
                        Conversation._conv_id_root = Container.instance.id
                except:
                    pass

        return "%s-%d" % (Conversation._conv_id_root, Conversation.conv_id_counter)


class ConversationEndpoint(object):

    def __init__(self, node):
        log.debug("In Conversation.__init__")
        self.node = node
        self._invitation_table = {} # mapping between role and public channels (principals)
        self._is_originator = False
        self._next_control_msg_type = 0
        self._recv_queues = {}


    @property
    def conv(self):
        return self._conv

    @conv.setter
    def protocol(self, value):
        self._conv = value

    """principal_addrs is addressable entity for that role (etc. NameTrio)"""
    # @TODO: Should we have existing channel
    def join(self, role, base_name, conversation , is_originator = False):
        self._conv = conversation
        self._self_role = role
        self._is_originator = is_originator
        self._chan = self.node.channel(BidirChannel)
        self._spawn_listener(role, base_name)

    def accept(self, inv_msg, inv_header, c, base_name, auto_reply = False):
        # @TODO: Fix that, nameTrio is too AMQP specific. better have short and long name for principal
        #endpoint.join(header['receiver-role'], NameTrio(self.name.exchange), c) # new channel will be generated based on the name
        self.join(inv_header['receiver-role'], base_name, c)
        self._on_msg_received(inv_msg, inv_header)
        print '_accept_invitation: Conversation added to the list'
        if auto_reply:
            self.send_ack(self.inviter_role, 'I am joining')

    def invite(self, to_role, to_role_addr, merge_with_first_send = True):
        print 'Invitation for address: %s' %(to_role_addr)
        self._invitation_table.setdefault(to_role, (to_role_addr, False))
        self._recv_queues.setdefault(to_role, gqueue.Queue())
        if not merge_with_first_send:
            header = {}
            header['conv-msg-type'] =  MSG_TYPE.INVITE
            header = self._build_invitation_header(header, to_role)
            self._send(to_role_addr, "", header)

    def send_ack(self, to_role, msg):
        header = {}
        to_role_addr = self._conv[to_role]
        header['conv-msg-type']  = MSG_TYPE.ACCEPT
        header = self._build_control_header(header, to_role, to_role_addr)
        self._send(to_role, to_role_addr, msg, header)
        self._next_control_msg_type = 0

    #@TODO: Shell we add **kwargs???, why we need them
    #@TODO: Pass User Headers
    def send(self, to_role, msg):
        if self._is_originator and not self._conv.has_role(to_role):
            _, is_invited  = self._invitation_table.get(to_role)
            print 'Is_invited:%s'  %is_invited
            if is_invited:
                self._send_in_session_msg(to_role, msg)
            else:
                self._invite_and_send(to_role, msg)
        else:
            self._send_in_session_msg(to_role, msg)
        #log.error('The role %s does not exists', to_role)
        #raise ConversationError('The role %s does not exists', to_role)

    def recv(self, from_role = None):
        print 'In Conversation.recv'
        msg, header = self._recv_queues[from_role].get()
        #@TODO: When to fuel the message through the intercept stack, when the msg is requested or when it is received?
        msg, header = self._intercept_msg_in(msg, header)
        return msg, header

    def close(self):
        if self._chan:
            # related to above, the close here would inject the ChannelShutdownMessage if we are NOT reusing.
            # we may end up having a duplicate, but I think logically it would never be a problem.
            # still, need to clean this up.
            self._chan.close()

        if self._recv_greenlet:
            # This is not entirely correct. We do it here because we want the listener's client_recv to exit gracefully
            # and we may be reusing the channel. This *SEEMS* correct but we're reaching into Channel too far.
            # @TODO: remove spawn_listener altogether.
            print 'I am in spawn and will kill the greenlet'
            self._chan._recv_queue.put(ChannelShutdownMessage())
            self._recv_greenlet.join(timeout=1)
            self._recv_greenlet.kill()      # he's dead, jim

    #@TODO: Do we need only one instance of a channel
    # We ahve preserved the logging from BaseEndpoint._spawn_listener
    def _spawn_listener(self, role, base_role_addr):
        def listen():
            print 'Conversation._spawn_listener'
            recv_chan = self.node.channel(ListenChannel)
            role_addr = recv_chan.setup_listener(NameTrio(base_role_addr))
            print 'Conversation.spawn_listener:role_addr: %s' %(role_addr)
            self._conv[role] = role_addr # this will block if there is no role in the _conv table, IS IT BAD???
            recv_chan.start_consume()
            while True:
                try:
                    log.debug("ConversationEndpoint_listen waiting for a message")
                    msg, header, delivery_tag =  recv_chan.recv()
                    log.debug("ConversationEndpoint_listen got a message")
                    log_message(role_addr , msg, header, delivery_tag)
                    try:
                        self._on_msg_received(msg, header)
                    finally:
                        # always ack listener response
                        recv_chan.ack(delivery_tag)
                except ChannelClosedError:
                    log.debug('Channel was closed during listen loop')
                    break
        self._recv_greenlet = spawn(listen)

    def _on_msg_received(self, msg, header):
        print 'in Conversation._on_msg_received'
        control_msg_type = get_control_msg_type(header)
        in_session_msg_type = get_in_session_msg_type(header)
        sender_role = header['sender-role']
        print 'Control msg type is:%s' %control_msg_type
        if control_msg_type == MSG_TYPE.ACCEPT or control_msg_type == MSG_TYPE.INVITE:
            print 'Inside Accept|Invite'
            self._recv_queues.setdefault(sender_role, gqueue.Queue())
            self._conv[sender_role] = NameTrio(tuple([x.strip() for x in header['reply-to'].split(',')]))
            if control_msg_type == MSG_TYPE.INVITE:
                self.inviter_role = sender_role
                #Note that if the message type is invite you need to accept it,
                # conversation endpoint is an endpoint that is in a conevrsation. Only principals can accept/reject
                #@ TODO: really need FSM mechanism here, optherwise it is so ugly :(
                self._next_control_msg_type = MSG_TYPE.ACCEPT
        elif control_msg_type == MSG_TYPE.REJECT:
            exception_msg = 'Invitation rejected by role %s on address %s'\
            %(header['sender-role'], header['reply-to'])
            log.exception(exception_msg)
            raise ConversationError(exception_msg)

        if in_session_msg_type == MSG_TYPE.TRANSMIT:
            self._recv_queues[sender_role].put((msg, header))

    def _invite_and_send(self, to_role, msg, header = None, to_role_addr = None):
        log.debug("In _invite_and_send for msg: %s", msg)

        if to_role_addr:
            self._invitation_table[to_role] =  (to_role_addr, False)
        elif to_role in self._invitation_table:
            to_role_addr, _ = self._invitation_table.get(to_role)
        else:
            log.debug('No address found for role %s', to_role)
            raise ConversationError('No receiver-addr specified')

        if not header: header = dict()
        header['conv-msg-type'] = MSG_TYPE.INVITE | MSG_TYPE.TRANSMIT
        to_role_addr, _ = self._invitation_table.get(to_role)
        self._invitation_table[to_role] = (to_role_addr, True)
        header = self._build_control_header(header, to_role, to_role_addr)
        print 'before sending: Role_addr: %s, Msg: %s, Header: %s' %(to_role_addr, msg, header)
        self._send(to_role, to_role_addr, msg, header)

    def _send_in_session_msg(self, to_role, msg, header = None):
        log.debug("In _send_in_session_msg: %s", msg)
        if not header: header = {}
        log.debug("In _send for msg: %s", msg)
        to_role_addr = self._conv[to_role]
        header['conv-msg-type']  = MSG_TYPE.TRANSMIT
        if (self._next_control_msg_type == MSG_TYPE.ACCEPT):
            header['conv-msg-type']  = header.get(['conv-msg-type'], 0) | MSG_TYPE.ACCEPT
            header = self._build_control_header(header, to_role, to_role_addr)
            self._next_control_msg_type = 0
        self._send(to_role, to_role_addr, msg, header)

    #@ Shell we add general build_header meant for overriding and general build_payload ???
    def _send(self, to_role, to_role_addr, msg, header = None):
        print 'In Conversation._send, to_role_addr is: %s, msg is:%s, header is: %s' %(to_role_addr, msg, header)
        # @TODO: Shell we combine build_header and _build_conv_header ???
        header = self._build_conv_header(header, to_role, to_role_addr)
        header = self._build_header(header)
        msg = self._build_payload(msg)
        msg, header = self._intercept_msg_out(msg, header)
        self._chan.connect(to_role_addr)
        self._chan.send(msg, header)

    #@TODO: We do not set reply-to, except for invite and accept ??? Is that correct.
    def _build_conv_header(self, header, to_role, to_role_addr):
        #@TODO shell we rename this to receiver-addr?
        header['receiver'] = "%s,%s" %(to_role_addr.exchange, to_role_addr.queue) #do we need that
        header['sender-role'] = self._self_role
        header['receiver-role'] = to_role
        header['conv-id'] = self._conv.id
        header['conv-seq'] = 1 # @TODO: Not done, How to track it: per role, per conversation ???
        header['protocol'] = self._conv.protocol
        return header

    def _build_control_header(self, header, to_role, to_role_addr):
        reply_to = self._conv[self._self_role]
        header['reply-to'] = "%s,%s" %(reply_to.exchange, reply_to.queue)
        return header

    #Copy from endpoint.py, EndpointUnit
    def _intercept_msg_in(self, msg, header):
        """
        Performs interceptions of incoming messages.
        Override this to change what interceptor stack to go through and ordering.

        @param  inv     An Invocation instance.
        @returns        A processed Invocation instance.
        """
        inv = self._build_invocation(path=Invocation.PATH_IN,
            message=msg, headers=header)

        inv_prime = process_interceptors(interceptors["message_incoming"] if "message_incoming" in interceptors else [], inv)

        return inv_prime.message, inv_prime.headers

    #Copy from endpoint.py, EndpointUnit
    def _intercept_msg_out(self, msg, header):
        """
        Performs interceptions of outgoing messages.
        Override this to change what interceptor stack to go through and ordering.

        @returns        message and header after being intercepted.
        """

        inv = self._build_invocation(path=Invocation.PATH_OUT,
                    message=msg, headers=header)
        inv_prime = process_interceptors(interceptors["message_outgoing"] if "message_outgoing" in interceptors else [], inv)

        return inv_prime.message, inv_prime.headers

    #Copy from endpoint.py, EndpointUnit
    def _build_invocation(self, **kwargs):
        """
        Builds an Invocation instance to be used by the interceptor stack.
        This method exists so we can override it in derived classes (ex with a process).
        """
        inv = Invocation(**kwargs)
        return inv

    def _build_header(self, header):
        """
        Override this method to set any custom settings
        """
        return header

    def _build_payload(self, msg):
        """
        Override this method to change the payload
        """
        return msg


class Principal(object):
    # keep the connection (AMQP)
    #@TODO: ensure node, may be by providing default broker connection

    def __init__(self, node, name = None):
       self.node = node
       self._name = name
       self._conversations = {}
       self._recv_queue = gqueue.Queue()
       self._chan = None
       self._recv_greenlet = None


    @property
    def base_name(self):
       return self.name.exchange

    @property
    def name(self):
       if not isinstance(self._name, NameTrio):
           self._name = NameTrio(bootstrap.get_sys_name(), self._name)
       return self._name

    #@TODO: In the endpoint.py implemenataion channel is decoupled from the spawn listener
    #@TODO: Do we need to spawn here? listen() method for all listeners is started in the thread_manager (in the process.py)
    # so may be we need to provide only listen and leave the upper level to take care of spawning?
    def spawn_listener(self, source_name = None):
       def listen():
           name = source_name or self.name
           #@TODO: Should we have separated create_channel method?, do we need kwargs for creating a channel,
           # kwargs is normally set pass for the initialisation of the channel depending on the channel type: chan = ch_type(**kwargs)
           self._chan = self.node.channel(ListenChannel)
           if name and isinstance(name, NameTrio):
               print 'In listen: before setup_listener'
               self._chan.setup_listener(name)
           else:
               log.debug('Principal.name is not correct: %s', name)
               raise PrincipalError('Principal.name is not correct: %s', name)

           self._chan.start_consume()
           while True:
               try:
                   with self._chan.accept() as newchan:
                       print 'Before receiving invitation msg'
                       msg, header, delivery_tag = newchan.recv()
                       print 'After receiving invitation msg: %s, %s' %(msg, header)
                       newchan.ack(delivery_tag)
                       self._recv_invitation(msg, header)
               except ChannelClosedError as ex:
                   log.debug('Channel was closed during LEF.listen')
                   break
       self._recv_greenlet = spawn(listen)

    def stop_listening(self):
        if self._chan:
            # related to above, the close here would inject the ChannelShutdownMessage if we are NOT reusing.
            # we may end up having a duplicate, but I think logically it would never be a problem.
            # still, need to clean this up.
            self._chan.close()

        if self._recv_greenlet:
           # This is not entirely correct. We do it here because we want the listener's client_recv to exit gracefully
           # and we may be reusing the channel. This *SEEMS* correct but we're reaching into Channel too far.
           # @TODO: remove spawn_listener altogether.
           self._chan._recv_queue.put(ChannelShutdownMessage())
           self._recv_greenlet.join(timeout=1)
           self._recv_greenlet.kill()      # he's dead, jim


    def get_invitation(self, protocol = None):
       # Here we should iterate while we find the protocol that is matched
       print 'Wait to get an invitation'
       return self._recv_queue.get() # this returns a conversations
       #if auto_reply:
       #    c.send_ack(c.inviter_role, 'I am joining')
       #return c

    def accept_invitation(self, c, msg, header, auto_reply = False):
       endpoint = ConversationEndpoint(self.node)
       endpoint.accept(msg, header, c, self.base_name, auto_reply)
       self._conversations[c.id] = c
       return endpoint

    def _recv_invitation(self, msg, header):
       control_msg_type = get_control_msg_type(header)
       if control_msg_type == MSG_TYPE.INVITE:
           c = Conversation(header['protocol'], header['conv-id'])
           print '_accept_invitation: Conversation added to the list'
           #self._conversations[header['conv-id']] = c
           self._recv_queue.put((c, msg, header))
           #else: raise ConversationError('Reject invitation is not supported yet.')

    def reject_invitation(self, msg, header):
       pass

    def check_invitation(self, msg, header):
       return True


class ConversationOriginator(Principal):
    def start_conversation(self, protocol, role):
       c = Conversation(protocol)
       endpoint = ConversationEndpoint(self.node)
       endpoint.join(role, self.base_name, is_originator = True, conversation = c) # join will generate new private channel based on the name
       self._conversations[c.id] = c
       return endpoint


#######################################################################################################################
# OOI specific (Container Specific) conversations
#######################################################################################################################


#######################################################################################################################
# RPC generic code
#######################################################################################################################

# Might be part of some hierarchy
# What is missing, how to set specific headers???
# header[performative] = 'request' ???
# also language, encoding, format, reply-by

class RPCClient(object):
    """
    Note: maybe we need RPCConversation and RPCOriginator, RPCPrincipal, they will return RPCClientEndpoint and RPCServerEndpoint
    """
    # Will be nice to have
    # combine requestresponseClient.request and RequestEndpointUnit._send
    s = 0
    def __init__(self, node, base_name, server_name):
        self.node = node
        self.name = base_name
        self.server_name = server_name

    def request(self, msg, header = None, **kwargs):
        # could have a specified timeout in kwargs
        if 'timeout' in kwargs and kwargs['timeout'] is not None:
            timeout = kwargs['timeout']
        else:
            timeout = CFG.endpoint.receive.timeout or 10

        log.debug("RequestEndpointUnit.send (timeout: %s)", timeout)

        ts = time.time()
        local = ConversationOriginator(self.node, self.name)
        c = local.start_conversation('rpc', 'client')
        c.invite('server', self.server_name)
        c.send('server', 'Hello%s'%self.s)
        try:
            result_data, result_headers = c.recv('server')
        except Timeout:
            raise exception.Timeout('Request timed out (%d sec) waiting for response from %s' % (timeout, str(self.channel._send_name)))
        finally:
            elapsed = time.time() - ts
            log.info("Client-side request (conv id: %s/%s, dest: %s): %.2f elapsed", header.get('conv-id', 'NOCONVID'),
                header.get('conv-seq', 'NOSEQ'),
                self.server_name,
                elapsed)
            c.close()
            local.stop_listening()
        log.debug("Response data: %s, headers: %s", result_data, result_headers)
        self.s+=1
        return result_data, result_headers

    def buy_bonds(self, msg):
        header = {}
        header['op'] = 'buy_bonds'
        return self.request(msg, header)

# Again, headers are missing
# This is indeed listener, and should be started in the process.py
# create_errro_response and make_routing_call are still missing
#@TODO; Implement. This is just a quick test, it is not a reasonable implementation of RPCServer
#@TODO: Headers are not set and _service is not called
class RPCServer(object):

    def __init__(self, node, name, service = None):
        self.node = node
        self.name = name
        self._service = service

    def listen(self):
            local = Principal(self.node, self.name)
            local.spawn_listener()
            while True:
                conv, msg, header  = local.get_invitation()
                c = local.accept_invitation(conv, msg, header, auto_reply = 'True')
                msg, header = c.recv('client')
                reply = self.process_msg(msg, header)
                c.send('client', reply)

    def process_msg(self, msg, header):
        if header.setdefault('op', '') == self._service:
            msg =  'Correct call. The message is:%s' %(msg)
            print msg
        else:
            msg = 'I do not support this call:%s' % (header['op'])
            print msg
        return msg

"""
So OOI specific RPCServer will hold a routing_object and will override process_msg to call the routing_obj (_service)
"""