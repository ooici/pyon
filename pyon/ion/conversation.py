from Queue import Empty
import uuid
from gevent.timeout import Timeout
from pyon.core import bootstrap, exception
from gevent import coros
from pyon.core.exception import IonException
from pyon.util.log import log
from pyon.net.transport import NameTrio
from pyon.net.channel import ListenChannel, ChannelClosedError, ChannelShutdownMessage, BidirClientChannel, SendChannel
from pyon.ion.endpoint import ProcessRPCClient, ProcessRPCServer, ProcessRPCResponseEndpointUnit, ProcessRPCRequestEndpointUnit
from pyon.core.interceptor.interceptor import Invocation
from gevent import queue as gqueue
from gevent.event import AsyncResult
from pyon.util.async import spawn
from pyon.util.containers import get_ion_ts
#@TODO: Fix this, the interceptors should be local, Conversation should not import endpoint
#@TODO: RPC specific import, should be removed
from pyon.core.bootstrap import CFG

def enum(**enums):
    return type('Enum', (), enums)

MSG_TYPE = enum(TRANSMIT = 1, INVITE=8, ACCEPT=16, REJECT = 24)
MSG_TYPE_MASKS = enum(IN_SESSION = 7, CONTROL= 56)


#@TODO: Add log.debug to all methods, can we do geenral on class level, except for typing it in every method?
#@TODO: How to manage **kwargs???
#@TODO: Add @param and @returns to all methods
#@TODO: Queues should be auto deleted

####################################################

class ConversationError(IonException):
    pass


class ParticipantError(IonException):
    pass


def enum(**enums):
    return type('Enum', (), enums)

def get_control_msg_type(header):
    if'conv-msg-type' in header:
        return header['conv-msg-type'] & MSG_TYPE_MASKS.CONTROL
    else: raise ConversationError('conv-msg-type in not set in the message header')

def get_in_session_msg_type(header):
    if 'conv-msg-type' in header:
        return header['conv-msg-type'] & MSG_TYPE_MASKS.IN_SESSION
    else: raise ConversationError('conv-msg-type in not set in the message header')

# @TODO: Do we need CLOSE ???
MSG_TYPE = enum(TRANSMIT = 1, INVITE=8, ACCEPT=16, REJECT = 24)
MSG_TYPE_MASKS = enum(IN_SESSION = 7, CONTROL= 56)

class Conversation(object):
    conv_id_counter = 0
    _lock = coros.RLock() #@TODO: is this safe?
    _conv_id_root = None

    def __init__(self, protocol, cid = None):
        self._conv_table = {}
        self._protocol = protocol
        self._id = cid if cid else self._build_conv_id()

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
    def id(self, value):
        self._id = value

    def __getitem__(self, to_role):
        self._conv_table.setdefault(to_role, AsyncResult())
        if isinstance(self._conv_table[to_role], AsyncResult):
            # @TODO. Need timeout for the AsyncResult
            to_role_addr = self._conv_table[to_role].get()
            self._conv_table[to_role] = to_role_addr
        return self._conv_table[to_role]

    def __setitem__(self, to_role, to_role_addr):
        log.debug("Conversation._add_to_conv_table: to_role:%s, to_role_addr:%s" %(to_role, to_role_addr))
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
        # mapping between role and public channels (participants)
        self._invitation_table = {}
        self._is_originator = False
        self._next_control_msg_type = 0
        self._recv_queues = {}
        self.endpoint_unit = None
        self.conv_seq = self.gen_conv_seq()

    def gen_conv_seq(self):
        x = 1
        while True:
            yield x
            x += 1

    @property
    def conv(self):
        return self._conv

    @conv.setter
    def conv(self, value):
        self._conv = value

    # @TODO: Should we have existing channel
    def join(self, role, base_name, conversation , is_originator = False):
        """principal_addrs is addressable entity for that role (etc. NameTrio)"""
        self._conv = conversation
        self._self_role = role
        self._is_originator = is_originator
        self._chan = self.node.channel(BidirClientChannel)
        #role_addr = recv_chan.setup_listener(NameTrio(base_name))
        role_addr = self._chan.setup_listener(NameTrio(base_name))
        if not role_addr:
            role_addr = self._chan._recv_name
        self._conv[self._self_role] = role_addr
        self._spawn_listener(self._chan)

    def accept(self, inv_msg, inv_header, c, base_name, auto_reply = False):
        #@TODO: Fix that, nameTrio is too AMQP specific. better have short and long name for principal
        self.join(inv_header['receiver-role'], base_name, c)
        self._on_msg_received(inv_msg, inv_header)
        if not auto_reply:
            self.send_ack(self.inviter_role, 'I am joining')

    def invite(self, to_role, to_role_addr, merge_with_first_send = False):
        """

        """
        self._invitation_table.setdefault(to_role, (to_role_addr, False))
        self._recv_queues.setdefault(to_role, gqueue.Queue())
        if not merge_with_first_send:
            header = {}
            to_role_addr = self._conv[to_role]
            header['conv-msg-type'] =  MSG_TYPE.INVITE
            header = self._build_control_header(header, to_role, to_role_addr)
            self._send(to_role_addr, "", header)

    def send_ack(self, to_role, msg):
        header = {}
        to_role_addr = self._conv[to_role]
        header['conv-msg-type']  = MSG_TYPE.ACCEPT
        header = self._build_control_header(header, to_role, to_role_addr)
        self._send(to_role, to_role_addr, msg, header)
        self._next_control_msg_type = 0

    #@TODO: Shell we add **kwargs???, why we need them
    #@TODO: We should pass User h, this version do not support
    def send(self, to_role, msg, header = None):
        header = header if header else {}
        if self._is_originator and not self._conv.has_role(to_role):
            _, is_invited  = self._invitation_table.get(to_role)
            if is_invited:
                self._send_in_session_msg(to_role, msg, header)
            else:
                self._invite_and_send(to_role, msg, header)
        else:
            self._send_in_session_msg(to_role, msg, header)

    def recv(self, from_role = None):
        (msg, header) = self._recv_queues[from_role].get()
        msg, header = self._intercept_msg_in(msg, header)
        log.debug("""\n
        ----------------Receiving message:-----------------------------------------------
        Message is: %s \n from %s to %s
        Header is: =%s  \n
        ----------------------------------------------------------------------------------
        """, msg, from_role, self._self_role, header)
        return msg, header

    def stop_conversation(self):
        self._chan.close()

        if self._recv_greenlet:
            # This is not entirely correct. We do it here because we want the listener's client_recv to exit gracefully
            # and we may be reusing the channel. This *SEEMS* correct but we're reaching into Channel too far.
            # @TODO: remove spawn_listener altogether.
            #self._chan._recv_queue.put(ChannelShutdownMessage())
            #self._recv_greenlet.join(timeout=1)
            self._recv_greenlet.kill()      # he's dead, jim

    #@TODO: Do we need only one instance of a channel
    def _spawn_listener(self, recv_chan):
        """
        We have preserved the logging from BaseEndpoint._spawn_listener
        """
        def listen():
            recv_chan.start_consume()
            while True:
                try:
                    log.debug("ConversationEndpoint_listen waiting for a message")
                    msg, header, delivery_tag =  recv_chan.recv()
                    log.debug("ConversationEndpoint_listen got a message")
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
        control_msg_type = get_control_msg_type(header)
        in_session_msg_type = get_in_session_msg_type(header)
        sender_role = header['sender-role']
        if control_msg_type == MSG_TYPE.ACCEPT or control_msg_type == MSG_TYPE.INVITE:
            self._recv_queues.setdefault(sender_role, gqueue.Queue())
            self._conv[sender_role] = NameTrio(tuple([x.strip() for x in header['reply-to'].split(',')]))
            if control_msg_type == MSG_TYPE.INVITE:
                self.inviter_role = sender_role

                #Note that if the message type is invite you need to accept it,
                #conversation endpoint is an endpoint that is in a conevrsation. Only
                #principals can accept/reject
                #@TODO: really need FSM mechanism here, optherwise it is so ugly :(
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
            log.debug("No address found for role %s", to_role)
            raise ConversationError('No receiver-addr specified')

        if not header: header = {}
        header['conv-msg-type'] = MSG_TYPE.INVITE | MSG_TYPE.TRANSMIT
        to_role_addr, _ = self._invitation_table.get(to_role)
        self._invitation_table[to_role] = (to_role_addr, True)
        header = self._build_control_header(header, to_role, to_role_addr)
        self._send(to_role, to_role_addr, msg, header)


    def _send_in_session_msg(self, to_role, msg, header = None):
        log.debug("In _send_in_session_msg: %s", msg)
        if not header: header = {}
        log.debug("In _send for msg: %s", msg)
        to_role_addr = self._conv[to_role]
        header['conv-msg-type']  = MSG_TYPE.TRANSMIT
        if self._next_control_msg_type == MSG_TYPE.ACCEPT:
            header['conv-msg-type']  = header.get('conv-msg-type', 0) | MSG_TYPE.ACCEPT
            header = self._build_control_header(header, to_role, to_role_addr)
            self._next_control_msg_type = 0
        self._send(to_role, to_role_addr, msg, header)

    #@TODO: Shell we combine build_header and _build_conv_header ?
    def _send(self, to_role, to_role_addr, msg, new_header = None):

        start = int(get_ion_ts())
        header = {}
        header = self._build_conv_header(header, to_role, to_role_addr)
        header = self._build_header(msg, header)
        msg = self._build_payload(msg)
        if new_header: header.update(new_header)
        msg, header = self._intercept_msg_out(msg, header)
        self._chan.connect(to_role_addr)
        elapsed = int(get_ion_ts()) - start
        log.debug("""\n
        ----------------Sending message:-----------------------------------------------
        Message is: %s from %s to %s
        Header is: =%s  \n
        ----------------------------------------------------------------------------------
        """, msg, self._self_role, to_role, header)
        self._chan.send(msg, header)

    #@TODO: We do not set reply-to, except for invite and accept ??? Is that correct.
    def _build_conv_header(self, header, to_role, to_role_addr):
        #@TODO shell we rename this to receiver-addr?
        header['receiver'] = "%s,%s" %(to_role_addr.exchange, to_role_addr.queue) #do we need that
        header['sender-role'] = self._self_role
        header['receiver-role'] = to_role
        header['conv-id'] = self._conv.id
        header['conv-seq'] = self.conv_seq.next() # @TODO: Not done, How to track it: per role, per conversation ???
        header['protocol'] = self._conv.protocol
        return header

    def _build_control_header(self, header, to_role, to_role_addr):
        reply_to = self._conv[self._self_role]
        header['reply-to'] = "%s,%s" %(reply_to.exchange, reply_to.queue)
        return header

    def _intercept_msg_in(self, msg, header):
        """
        Performs interceptions of incoming messages.
        @returns        A processed Invocation instance.
        """
        if self.endpoint_unit:
            msg, header = self.endpoint_unit.intercept_in(msg, header)

        return msg, header

    def _intercept_msg_out(self, msg, header):
        """
        Performs interceptions of outgoing messages.
        @returns        message and header after being intercepted.
        """
        if self.endpoint_unit:
            msg, header = self.endpoint_unit.intercept_out(msg, header)

        return msg, header


    #Copy from endpoint.py, EndpointUnit
    def _build_invocation(self, **kwargs):
        """
        Builds an Invocation instance to be used by the interceptor stack.
        This method exists so we can override it in derived classes (ex with a process).
        """
        if self.endpoint_unit:
            inv = self.endpoint_unit._build_invocation(**kwargs)
        else: inv = Invocation(**kwargs)
        return inv

    def _build_header(self, msg, header):
        """
        Override this method to set any custom settings
        """
        if self.endpoint_unit:
            header.update(self.endpoint_unit._build_header(msg, header))
        """
        Below headers are set by the base_endpoint classes
        header['language'] = 'ion-r2'
        header['encoding'] = 'msgpack'
        header['format']   = msg.__class__.__name__    # hmm
        header['reply-by'] = 'todo'                        # clock sync is a problem
        """
        return header

    def _build_payload(self, msg):
        """
        Override this method to change the payload
        """
        return msg

    def attach_endpoint_unit(self, endpoint_unit):
        self.endpoint_unit = endpoint_unit

class Participant(object):
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
    def start_listening(self, source_name = None):
        def listen():
            name = source_name or self.name
            #@TODO: Should we have separated create_channel method?, do we need kwargs for creating a channel,
            # kwargs is normally set pass for the initialisation of the channel depending on the channel type: chan = ch_type(**kwargs)
            self._chan = self.node.channel(ListenChannel)
            if name and isinstance(name, NameTrio):
                self._chan.setup_listener(name)
            else:
                log.debug('Participant.name is not correct: %s', name)
                raise ParticipantError('Participant.name is not correct: %s', name)

            self._chan.start_consume()
            while True:
                try:
                    newchan =self._chan.accept()
                    msg, header, delivery_tag = newchan.recv()
                    newchan.ack(delivery_tag)
                    self._recv_invitation(msg, header)
                except ChannelClosedError as ex:
                    log.debug('Channel was closed during LEF.listen')
                    break
        self._recv_greenlet = spawn(listen)

    def stop_listening(self):
        [conv_endpoint.close() for conv_endpoint  in self._conversations.values()]

    def start_conversation(self, protocol, role):
        c = Conversation(protocol)
        endpoint = ConversationEndpoint(self.node)
        endpoint.join(role, self.base_name, is_originator = True, conversation = c) # join will generate new private channel based on the name
        self._conversations[c.id] = endpoint
        return endpoint

    def terminate(self):
        #@TODO: Fix that
        #[c.stop_conversation() for c  in self._conversations]
        if self._chan:
            # related to above, the close here would inject the ChannelShutdownMessage if we are NOT reusing.
            # we may end up having a duplicate, but I think logically it would never be a problem.
            # still, need to clean this up.
            self._chan.close()

        if self._recv_greenlet is not None:
            # This is not entirely correct. We do it here because we want the listener's client_recv to exit gracefully
            # and we may be reusing the channel. This *SEEMS* correct but we're reaching into Channel too far.
            # @TODO: remove spawn_listener altogether.
            self._chan._recv_queue.put(ChannelShutdownMessage())
            self._recv_greenlet.join(timeout=1)
            self._recv_greenlet.kill()      # he's dead, jim

    def get_invitation(self, protocol = None):
        log.debug('Wait to get an invitation')
        return self._recv_queue.get() # this returns a conversations

    def accept_invitation(self, invitation, merge_with_first_send = False):
        (c, msg, header) =  invitation
        endpoint = ConversationEndpoint(self.node)
        endpoint.accept(msg, header, c, self.base_name, merge_with_first_send)
        self._conversations[c.id] = endpoint
        log.debug("""\n
        ----------------Accepting invitation:-----------------------------------------------
        Header is: =%s  \n
        ----------------------------------------------------------------------------------
        """, header)
        return endpoint

    def accept_next_invitation(self, merge_with_first_send = False):
        invitation = self.get_invitation()
        return self.accept_invitation(invitation, merge_with_first_send)

    def _recv_invitation(self, msg, header):
        control_msg_type = get_control_msg_type(header)
        if control_msg_type == MSG_TYPE.INVITE:
            c = Conversation(header['protocol'], header['conv-id'])
            log.debug('_accept_invitation: Conversation added to the list')
            self._recv_queue.put((c, msg, header))
            #else: raise ConversationError('Reject invitation is not supported yet.')

    def reject_invitation(self, msg, header):
        pass

    def check_invitation(self, msg, header):
        return True


#######################################################################################################################
# OOI specific (Container Specific) conversations
#######################################################################################################################


#######################################################################################################################
# RPC generic code
#######################################################################################################################

class RPCRequesterEndpoint(object):

    # Will be nice to have
    # combine requestresponseClient.request and RequestEndpointUnit._send

    def __init__(self, endpoint_unit = None):
        self.endpoint_unit = endpoint_unit

    '''
    def __init__(self, node, base_name, server_name,
                 rpc_conversation = None, endpoint_unit = None):
        self.node = node
        self.name = base_name
        self.server_name = server_name
        self.rpc_conv = rpc_conversation or RPCConversation()
        self.participant = Participant(self.node, self.name)
        self.endpoint_unit = endpoint_unit


    def send(self, msg, headers , **kwargs):
        # could have a specified timeout in kwargs
        if 'timeout' in kwargs and kwargs['timeout'] is not None:
            timeout = kwargs['timeout']
        else:
            timeout = CFG.get_safe('endpoint.receive.timeout', 10)

        ts = int(get_ion_ts())
        # we have a timeout, update reply-by header
        headers['reply-by'] = str(ts + timeout * 1000)



        log.debug("RequestEndpointUnit.send (timeout: %s)", timeout)

        c = self.participant.start_conversation(self.rpc_conv.protocol, self.rpc_conv.client_role)
        if self.endpoint_unit:
            c.attach_endpoint_unit(self.endpoint_unit)
        c.invite(self.rpc_conv.server_role, self.server_name, merge_with_first_send = True)
        c.send(self.rpc_conv.server_role, msg, headers)

        try:
            result_data, result_headers = c.recv(self.rpc_conv.server_role)
        except Timeout:
            raise exception.Timeout('Request timed out (%d sec) waiting for response from %s' % (timeout, str(self.name)))
        finally:
            elapsed = int(get_ion_ts()) - ts
            log.debug("Client-side request (conv id: %s/%s, dest: %s): %.2f elapsed", headers.get('conv-id', 'NOCONVID'),
                     headers.get('conv-seq', 'NOSEQ'),
                self.server_name,
                elapsed)
            c.stop_conversation()
            if self.endpoint_unit:
                self.endpoint_unit.close()
        log.debug("Response data: %s, headers: %s", result_data, result_headers)
        return result_data, result_headers

    def terminate(self):
        self.participant.terminate()

    def close(self):
        self.terminate()
    '''

#@TODO; Implement. This is just a quick test, it is not a reasonable implementation of RPCServer
#@TODO: Headers are not set and _service is not called
class RPCProviderEndpoint(object):
    """
    Again, headers are missing
    This is indeed listener, and should be started in the process.py
    create_errro_response and make_routing_call are still missing
    """
    def __init__(self, endpoint_unit = None):
        self.endpoint_unit = endpoint_unit




    '''
    def __init__(self, node, name, service = None, rpc_conversation = None, endpoint_unit = None):
        self.node = node
        self.name = name
        self._service = service
        self.rpc_conv = rpc_conversation or RPCConversation()
        self.participant = Participant(self.node, self.name)
        self.endpoint_unit = endpoint_unit

    def listen(self):
        self.participant.start_listening()

    def attach_endpoint_unit(self, endpoint_unit):
        self.endpoint_unit = endpoint_unit


    class MessageObject(object):
        def __init__(self, full_msg):
            self.full_msg = full_msg

        def route(self):
            pass

        def ack(self):
            pass

    def get_one_msg(self):
        try:
            ts = get_ion_ts()
            c = self.participant.accept_next_invitation(merge_with_first_send = True)
            #log.debug("LEF %s received message %s, headers %s, delivery_tag %s", self._recv_name, "-", headers, delivery_tag)
            #log_message(self._recv_name, msg, headers, delivery_tag)
            if self.endpoint_unit:
                c.attach_endpoint_unit(self.endpoint_unit)
            try:
                msg, header = c.recv(self.rpc_conv.client_role)
                reply, reply_header = self.process_msg(msg, header)
                msg_to_return = self.MessageObject(reply)
                c.send(self.rpc_conv.client_role, reply, reply_header)
                if msg == 'quit':
                    self.participant.terminate()
            except Exception:
                log.exception("Unhandled error while handling received message")
                raise
            finally:
                c.stop_conversation()
        except Empty:
            # only occurs when timeout specified, capture the Empty we get from accept and return False
            #TODO: handle Channel exceptions, not general ones
            pass

        return msg_to_return

    def process_msg(self, msg, header):
        return ''

    def terminate(self):
        self.participant.terminate()
    '''

class RPCConversation(object):
    def __init__(self, protocol = None, server_role = None, client_role = None):
        self.protocol = protocol or 'rpc'
        self.server_role = server_role or 'provider'
        self.client_role = client_role or 'requester'

class ParticipantName(object):
    def __init__(self, namespace, name):
        self.name = NameTrio(namespace, name)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

class ConversationProcessRPCRequestEndpointUnit(ProcessRPCRequestEndpointUnit):

    def __init__(self, **kwargs):
        self.participant = RPCRequesterEndpoint(self)
        ProcessRPCRequestEndpointUnit.__init__(self, **kwargs)


    def send(self, msg, headers=None, **kwargs):
        return ProcessRPCRequestEndpointUnit.send(self, msg, headers,  **kwargs)


class ConversationRPCClient(ProcessRPCClient):
    endpoint_unit_type = ConversationProcessRPCRequestEndpointUnit

    def create_endpoint(self, to_name=None, existing_channel=None, **kwargs):
        return ProcessRPCClient.create_endpoint(self, to_name, existing_channel, **kwargs)


class ConversationProcessRPCResponseEndpointUnit(ProcessRPCResponseEndpointUnit):

    def __init__(self, **kwargs):
        self.participant = RPCProviderEndpoint(self)
        ProcessRPCResponseEndpointUnit.__init__(self, **kwargs)


    def message_received(self, msg, headers):
        result, response_headers = ProcessRPCResponseEndpointUnit.message_received(self, msg, headers)

        return result, response_headers

    def send(self, msg, headers=None, **kwargs):
        return ProcessRPCResponseEndpointUnit.send(self, msg, headers,  **kwargs)


class ConversationRPCServer(ProcessRPCServer):
    endpoint_unit_type = ConversationProcessRPCResponseEndpointUnit

    def create_endpoint(self, **kwargs):
        return ProcessRPCServer.create_endpoint(self, **kwargs)

    '''

    def get_one_msg(self, num=1, timeout=None):
        e = self.create_endpoint()
        self.participant.attach_endpoint_unit(e)
        self.participant.process_msg = lambda m, h: e.message_received(m, h)
        return self.participant.get_one_msg()

    def prepare_listener(self, binding = None):
        self.participant =  RPCProviderEndpoint(self.node, self._recv_name)
        self.participant.listen()

    def deactivate(self):
        self.participant.stop_listening()

    def close(self):
        self.participant.terminate()
        #super(ConversationRPCServer, self).close()

    '''