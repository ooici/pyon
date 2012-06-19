import uuid
from gevent import coros
from pyon.core.exception import IonException
from pyon.util.log import log
from pyon.net.transport import NameTrio, BaseTransport
from pyon.net.channel import ChannelError, ChannelClosedError, BaseChannel, BidirClientChannel, ChannelShutdownMessage


class ConversationError(IonException):
    pass

def enum(**enums):
    return type('Enum', (), enums)

# @TODO: Do we need CLOSE ???
MSG_TYPE = enum(TRANSMIT = 1, INVITE=2, ACCEPT=4, REJECT = 6)

class Conversation(object):
    # mapping between role and channels
    _conv_table = {}
    _invitation_table = {}
    _conv_id = None
    _self_role = None
    _protocol = None
    _chan = None
    _next_control_msg_type = 0


    """_buil_conv specific variables"""
    conv_id_counter = 0
    _lock = coros.RLock()       # @TODO: is this safe?
    _conv_id_root = None

    def __init__(self, protocol):
        log.debug("In Conversation.__init__")

    """invitation table should be of the form: role_name = NameTrio"""
    @classmethod
    def create(cls, node, protocol, **invitation_table):
        # kwargs are role_name: NameTrio
        c = Conversation()
        c.node = node
        c.protocol = protocol
        c.invitation_table.update(invitation_table)
        c._conv_id = c._build_conv_id()

    """principal_addrs is addressable entity for that role (etc. NameTrio)"""
    def join(self, role, role_addr, binding = None):
        self._self_role = role
        self._conv_table.setdefault(role, role_addr)
        self._chan = self.node.channel(BidirClientChannel)
        self._chan.setup_listener(role_addr, binding)
        self._chan.start_consume()

    def send(self, to_role, msg):
        if to_role in self._conv_table:
            self._send(to_role, msg)
        elif to_role in self._invitation_table:
            self._invite_and_send(to_role, msg)
        else:
            log.error('The role %s does not exists', to_role)
            raise ConversationError('The role %s does not exists', to_role)

    # This is only for private channels
    def receive(self):
        msg =  self._chan.recv()
        if msg.header['conv-msg-type'] == self.MSG_TYPE.TRANSMIT:
            return msg


    def _receive(self, from_role, msg):
        # @TODO: FIX get from the queue .....
        # @TODO: FIX
        control_msg_type = msg.headers['conv-msg-type']
        normal_msg_type = msg.headers['conv-msg-type']

        if control_msg_type == self.MSG_TYPE.INVITE:
            if self._check_invitation(msg):
                # Initialize conversation table
                self._next_control_msg_type = self.MSG_TYPE.ACCEPT
                self._conv_table = msg.headers['conv-table']
            else: self._next_control_msg_type = self.MSG_TYPE.ACCEPT

        elif control_msg_type == self.MSG_TYPE.ACCEPT:
            # @TODO:Fix: reply-to should be renamed to sender-addr
            self._conv_table.setdefault(msg.headers['sender-role'], msg.headers['reply-to'])
        elif control_msg_type == self.MSG_TYPE.REJECT:
            exception_msg = 'Invitation rejected by role %s on address %s' \
                            %(msg.headers['sender-role'], msg.headers['reply-to'])
            log.exception(exception_msg)
            raise ConversationError(exception_msg)

        if normal_msg_type == self.MSG_TYPE.TRANSMIT:
            return msg

        #@TODO: Check the conv-msg-type header for correctness
        #log.exception('Message type is not recognized %s', msg.headers['conv_msg-type'])
        #raise ConversationError('Message type is not recognized %s', msg.headers['conv_msg-type'])

    # TODO: Why we need the counter here?. This is a copy from endpoint.py, it should change
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


    def invite_and_send(self, to_role, msg, to_role_addr = None):
        log.debug("In _invite_and_send for msg: %s", msg)
        # set header['conv-msg-type'] = 'transmit'
        msg.headers['conv-msg-type'] == self.MSG_TYPE.INVITE |self.MSG_TYPE.TRANSMIT
        #############################conversation table############################
        msg.headers['sender-role'] = self._self_role
        msg.headers['reply-to'] = conv_table.get(self._self_role)
        ###########################################################################
        msg.headers['receiver-role'] = to_role # do we need that
        msg.headers['receiver-addr'] = _invitation_table.get(to_role) #do we need that

        if to_role_addr: self._invitation_table.setdefault(to_role)
        elif to_role in self._invitation_table:
            to_role_addr = self._invitation_table.get(to_role)
        else:
            log.debug('No address found for role %s', to_role)
            raise ConversationError('No receiver-addr specified')
        self._chan.send(to_role_addr)

    def _send(self, to_role, msg):
        log.debug("In _send for msg: %s", msg)
        # @TODO: set the headers
        msg.headers['sender-role'] = self._self_role
        msg.headers['receiver-role'] = to_role
        self._chan.send(self._conv_table.get(to_role))
        msg.headers['conv-msg-type'] == self.MSG_TYPE.TRANSMIT|self._next_control_msg_type


    def _check_invitation(self, msg):
        return True
class Principal(object):
    # mapping between conv_id and conversation instance
    _conversations = {}
    _recv_queue = None
    # keep the connection (AMQP)
    node = None

    def __init__(self, node, name):
        self.node = node
        self.name = name

    def listen(self):
        # create channel and listen on it
        # receive_invitation should be processed when something is received
        pass

    def receive_invitation(self, msg):
        control_msg_type = msg.headers['conv-msg-type']
        if control_msg_type == self.MSG_TYPE.INVITE:
            if self._check_invitation(msg):
                self.accept_invitation(msg)
            else: raise ConversationError('Reject invitation is not supported yet.')
        elif control_msg_type == self.MSG_TYPE.ACCEPT:
            # @TODO:Fix: reply-to should be renamed to sender-addr
            c = self._conversations.get(msg.header['conv-id'])
            c.setdefault(msg.headers['sender-role'], msg.headers['reply-to'])
        elif control_msg_type == self.MSG_TYPE.REJECT:
            exception_msg = 'Invitation rejected by role %s on address %s'\
            %(msg.headers['sender-role'], msg.headers['reply-to'])
            log.exception(exception_msg)
            raise ConversationError(exception_msg)

    def accept_invitation(self, msg):
        # Initialize conversation table
        c = Conversation.create(self.node, msg.header['protocol'])
        c.join(msg.header['sender-role'], self.name) # new channel will be generated based on the name
        self._conversations.setdefault(msg.header['conv-id'], c)
        self._recv_queue.put(c)
        return c
        # @TODO: get the node
        # c._conv_table = msg.headers['conv-table']

    def _check_invitation(self, msg):
        pass

    def get_invitation(self, protocol = None):
        # Here we should iterate while we find the protocol that is matched
        return self.recv_queue.get()

class ConversationOriginator(Principal):
    def start_conversation(self, protocol, role):
        c = Conversation.create(self.node, protocol)
        c.join(role, self.name) # join will generate new private channel based on the name
        self._conversations.setdefault(c._conv_id, c)
        return c