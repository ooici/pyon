import uuid
import collections
from gevent import coros
from pyon.core.exception import IonException
from pyon.util.log import log
from pyon.net.transport import NameTrio, BaseTransport
from pyon.net.channel import BidirChannel, ChannelClosedError, ChannelShutdownMessage
from gevent import queue as gqueue
from gevent.event import AsyncResult
from pyon.util.async import spawn, switch


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
    _conv_table = {} # mapping between role and private channels
    _invitation_table = {} # mapping between role and public channels (principals)
    _is_originator = False
    _conv_id = None
    _self_role = None
    _protocol = None
    _chan = None
    _next_control_msg_type = 0
    _recv_queues = {}
    _recv_greenlet = None
    inviter_role = None

    """_buil_conv specific variables"""
    conv_id_counter = 0
    _lock = coros.RLock()       # @TODO: is this safe?
    _conv_id_root = None

    def __init__(self, protocol):
        log.debug("In Conversation.__init__")
        self._protocol = protocol

    """invitation table should be of the form: role_name = NameTrio"""
    @classmethod
    def create(cls, node, protocol,cid = None, **invitation_table):
        # kwargs are role_name: NameTrio
        c = Conversation(protocol)
        c.node = node
        c.protocol = protocol
        c._invitation_table.update(invitation_table)
        if cid: c._conv_id = cid
        else:   c._conv_id = c._build_conv_id()
        return c

    """principal_addrs is addressable entity for that role (etc. NameTrio)"""
    # @TODO: Should we have existing channel
    def join(self, role, role_addr, existing_channel = None, is_originator = False):
        self._self_role = role
        #self._chan.attach_observer(self.on_msg_deliver_handler)
        self._is_originator = is_originator
        print 'Is_Originator is : %s' %(self._is_originator)
        self._chan = existing_channel or self.node.channel(BidirChannel)
        self._spawn_listener(role, role_addr)

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
        to_role_addr = self._get_from_conv_table(to_role)
        header['conv-msg-type']  = MSG_TYPE.ACCEPT
        header = self._build_control_header(header, to_role, to_role_addr)
        self._send(to_role, to_role_addr, msg, header)
        self._next_control_msg_type = 0

    def send(self, to_role, msg):
        if self._is_originator and not to_role in self._conv_table:
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
        return self._recv_queues[from_role].get()

    def close(self):
        if self._recv_greenlet is not None:
            # This is not entirely correct. We do it here because we want the listener's client_recv to exit gracefully
            # and we may be reusing the channel. This *SEEMS* correct but we're reaching into Channel too far.
            # @TODO: remove spawn_listener altogether.
            self._chan._recv_queue.put(ChannelShutdownMessage())
            self._recv_greenlet.join(timeout=2)
            self._recv_greenlet.kill()      # he's dead, jim

        if self._chan is not None:
            # related to above, the close here would inject the ChannelShutdownMessage if we are NOT reusing.
            # we may end up having a duplicate, but I think logically it would never be a problem.
            # still, need to clean this up.
            self._chan.close()

    def _spawn_listener(self, role, base_role_addr):
        def listen():
            print 'Conversation._spawn_listener'
            role_addr = self._chan.setup_listener(base_role_addr)
            print 'Conversation.spawn_listener:role_addr: %s' %(role_addr)
            self._add_to_conv_table(role, role_addr)
            self._chan.start_consume()
            while True: self._on_msg_deliver_handler()
        self._recv_greenlet = spawn(listen)

    def _on_msg_deliver_handler(self):
        print 'in Conversation.on_msg_deliver_handler'
        msg, header, delivery_tag =  self._chan.recv()
        self._on_msg_received(msg, header)
        self._chan.ack(delivery_tag)

    def _on_msg_received(self, msg, header):
        print 'in Conversation._on_msg_received'
        control_msg_type = get_control_msg_type(header)
        in_session_msg_type = get_in_session_msg_type(header)
        if control_msg_type == MSG_TYPE.ACCEPT:
            # @TODO-Fix: reply-to should be renamed to sender-addr
            self._add_to_conv_table(header['sender-role'], NameTrio(tuple([x.strip() for x in header['reply-to'].split(',')])))
        elif control_msg_type == MSG_TYPE.REJECT:
            exception_msg = 'Invitation rejected by role %s on address %s'\
            %(header['sender-role'], header['reply-to'])
            log.exception(exception_msg)
            raise ConversationError(exception_msg)
        elif control_msg_type == MSG_TYPE.INVITE:
            # Initialize conversation table ... for now it is only reply-to
            self._add_to_conv_table(header['sender-role'], NameTrio(tuple([x.strip() for x in header['reply-to'].split(',')])))
            self.inviter_role = header['sender-role']
            self._next_control_msg_type = MSG_TYPE.ACCEPT

        if in_session_msg_type == MSG_TYPE.TRANSMIT:
            self._recv_queues[header['sender-role']].put((msg, header))

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
        to_role_addr = self._get_from_conv_table(to_role)
        header['conv-msg-type']  = MSG_TYPE.TRANSMIT
        if (self._next_control_msg_type == MSG_TYPE.ACCEPT):
            header['conv-msg-type']  = header.get(['conv-msg-type'], 0) | MSG_TYPE.ACCEPT
            header = self._build_control_header(header, to_role, to_role_addr)
            self._next_control_msg_type = 0
        self._send(to_role, to_role_addr, msg, header)

    def _send(self, to_role, to_role_addr, msg, header = None):
        print 'In Conversation._send, to_role_addr is: %s, msg is:%s, header is: %s' %(to_role_addr, msg, header)
        header = self._build_conv_header(header, to_role, to_role_addr)
        self._chan.connect(to_role_addr)
        self._chan.send(msg, header)

    #@TODO: We do not set reply-to, except for invite and accept ??? Is that correct.
    def _build_conv_header(self, header, to_role, to_role_addr):
        #@TODO shell we rename this to receiver-addr?
        header['receiver'] = "%s,%s" %(to_role_addr.exchange, to_role_addr.queue) #do we need that
        header['sender-role'] = self._self_role
        header['receiver-role'] = to_role
        header['conv-id'] = self._conv_id
        header['conv-seq'] = 1 # @TODO: Not done, How to track it: per role, per conversation ???
        header['protocol'] = self._protocol
        return header

    def _build_control_header(self, header, to_role, to_role_addr):
        reply_to = self._get_from_conv_table(self._self_role)
        header['reply-to'] = "%s,%s" %(reply_to.exchange, reply_to.queue)
        return header

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
                try:
                    from pyon.container.cc import Container
                    if Container.instance and Container.instance.id:
                        Conversation._conv_id_root = Container.instance.id
                except:
                    pass

        return "%s-%d" % (Conversation._conv_id_root, Conversation.conv_id_counter)

    def _add_to_conv_table(self, to_role, to_role_addr):
        print 'Conversation._add_to_conv_table: to_role:%s, to_role_addr:%s' %(to_role, to_role_addr)
        self._recv_queues.setdefault(to_role, gqueue.Queue())
        if to_role in self._conv_table and isinstance(self._conv_table[to_role], AsyncResult):
            self._conv_table[to_role].set(to_role_addr)
        else: self._conv_table[to_role] = to_role_addr

    def _get_from_conv_table(self, to_role):
        print "In._get_from_conv_table"
        self._conv_table.setdefault(to_role, AsyncResult())
        if isinstance(self._conv_table[to_role], AsyncResult):
            # @TODO. Need timeout for the AsyncResult
            print "Wait on the Async Result"
            to_role_addr = self._conv_table[to_role].get()
            print "get the Async Result, value is:%s" %to_role_addr
            self._conv_table[to_role] = to_role_addr
        return self._conv_table[to_role]


class Principal(object):
    # mapping between conv_id and conversation instance
    _conversations = {}
    _recv_queue = gqueue.Queue()
    _recv_greenlet = None
    _chan = None
    # keep the connection (AMQP)
    node = None
    name = None

    def __init__(self, node, name = None):
        self.node = node
        self.name = name

    def spawn_listener(self, source_name = None):
        def listen():
            name = source_name or self.name
            self._chan = self.node.channel(BidirChannel)
            if name and isinstance(name, NameTrio):
                print 'In listen: before setup_listener'
                self._chan.setup_listener(name)
            else:
                log.debug('Principal.name is not correct: %s', name)
                raise PrincipalError('Principal.name is not correct: %s', name)

            self._chan.start_consume()
            try:
                with self._chan.accept() as newchan:
                    print 'Before receiving invitation msg'
                    msg, header, delivery_tag = newchan.recv()
                    print 'After receiving invitation msg: %s, %s' %(msg, header)
                    newchan.ack(delivery_tag)
                    self._recv_invitation(msg, header)
            except ChannelClosedError as ex:
                log.debug('Channel was closed during LEF.listen')
        self._recv_greenlet = spawn(listen)

    def stop_listening(self):
        if self._recv_greenlet is not None:
            # This is not entirely correct. We do it here because we want the listener's client_recv to exit gracefully
            # and we may be reusing the channel. This *SEEMS* correct but we're reaching into Channel too far.
            # @TODO: remove spawn_listener altogether.
            self._chan._recv_queue.put(ChannelShutdownMessage())
            self._recv_greenlet.join(timeout=2)
            self._recv_greenlet.kill()      # he's dead, jim

        if self._chan is not None:
            # related to above, the close here would inject the ChannelShutdownMessage if we are NOT reusing.
            # we may end up having a duplicate, but I think logically it would never be a problem.
            # still, need to clean this up.
            self._chan.close()

    def get_invitation(self, protocol = None, auto_reply = False):
        # Here we should iterate while we find the protocol that is matched
        print 'Wait to get an invitation'
        c = self._recv_queue.get() # this returns a conversations
        if auto_reply:
            c.send_ack(c.inviter_role, 'I am joining')
        return c

    def _recv_invitation(self, msg, header):
        print '_recv_invitation'
        control_msg_type = get_control_msg_type(header)
        if control_msg_type == MSG_TYPE.INVITE:
            print 'Control msg type is INVITE'
            if self._check_invitation(msg, header):
                self._accept_invitation(msg, header)
            else: raise ConversationError('Reject invitation is not supported yet.')

    def _accept_invitation(self, msg, header):
        # Initialize conversation table
        msg_type = get_in_session_msg_type(header)
        c = Conversation.create(self.node, header['protocol'], header['conv-id'])
        # @TODO: Fix that, nameTrio is too AMQP specific. better have short and long name for principal
        c.join(header['receiver-role'], NameTrio(self.name.exchange)) # new channel will be generated based on the name
        c._on_msg_received(msg, header)
        print '_accept_invitation: Conversation added to the list'
        self._conversations[header['conv-id']] = c
        self._recv_queue.put(c)

    def _reject_invitation(self, msg, header):
        pass

    def _check_invitation(self, msg, header):
        return True


class ConversationOriginator(Principal):
    def start_conversation(self, protocol, role):
        c = Conversation.create(self.node, protocol)
        c.join(role, self.name, is_originator = True) # join will generate new private channel based on the name
        self._conversations[c._conv_id] = c
        return c