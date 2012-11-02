
from pyon.core import bootstrap, exception
from pyon.core.exception import IonException
from pyon.util.log import log
from pyon.net.transport import NameTrio
from pyon.ion.endpoint import ProcessRPCClient, ProcessRPCServer, ProcessRPCResponseEndpointUnit, ProcessRPCRequestEndpointUnit
from gevent import queue as gqueue
from gevent.event import AsyncResult


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

    def __init__(self, protocol, cid = None):
        self._conv_table = {}
        self._protocol = protocol
        if not cid:
            raise ConversationError('A conversation id was not specified')
        self._id = cid

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
        self._conv_table[to_role]

    def __setitem__(self, to_role, to_role_name):
        log.debug("Conversation._add_to_conv_table: to_role:%s, to_role_addr:%s" %(to_role, to_role_name))
        self._conv_table[to_role] = to_role_name

    def has_role(self, role):
        return role in self._conv_table


class ConversationEndpoint(object):

    def __init__(self, end_point_unit):
        log.debug("In Conversation.__init__")
        self._end_point_unit = end_point_unit

        # mapping between role and public channels (participants)
        self._invitation_table = {}
        self._is_originator = False
        self._next_control_msg_type = 0

    def get_conversation_id(self):
        if hasattr(self, '_conversation') and self._conversation:
            return self._conversation.id
        return None

    def join(self, role, conversation, is_originator = False):
        self._conversation = conversation
        self._self_role = role
        self._is_originator = is_originator

    def accept(self, invite_msg, invite_headers, c, auto_reply = False):
        if invite_headers.has_key('receiver-role'):
            self.join(invite_headers['receiver-role'], c)

        self._msg_received(invite_msg, invite_headers)
        if not auto_reply:
            self.send_ack(self.inviter_role, 'I am joining')

    def send_ack(self, to_role, msg):
        header = {}
        to_role_name = self._conversation[to_role]
        header['conv-msg-type']  = MSG_TYPE.ACCEPT
        self._send(to_role, to_role_name, msg, header)
        self._next_control_msg_type = 0


    def invite(self, to_role, to_role_name, merge_with_first_send = False):
        self._invitation_table.setdefault(to_role, (to_role_name, False))
        if not merge_with_first_send:
            headers = {}
            to_role_name = self._conversation[to_role]
            headers['conv-msg-type'] =  MSG_TYPE.INVITE
            self._send(to_role, to_role_name, "", headers)

    def send(self, to_role, msg, headers = None):
        header = headers if headers else {}
        if self._is_originator and not self._conversation.has_role(to_role):
            _, is_invited  = self._invitation_table.get(to_role)
            if is_invited:
                return self._send_in_session_msg(to_role, msg, headers)
            else:
                return self._invite_and_send(to_role, msg, headers)
        else:
            return self._send_in_session_msg(to_role, msg, headers)

    def _invite_and_send(self, to_role, msg, headers = None, to_role_name = None):
        log.debug("In _invite_and_send for msg: %s", msg)
        header = headers if headers else {}
        if to_role_name:
            self._invitation_table[to_role] =  (to_role_name, False)
        elif to_role in self._invitation_table:
            to_role_name, _ = self._invitation_table.get(to_role)
        else:
            msg = 'No to_role_name found in invitation table for %s' % to_role
            log.debug(msg)
            raise ConversationError(msg)


        header['conv-msg-type'] = MSG_TYPE.INVITE | MSG_TYPE.TRANSMIT
        to_role_name, _ = self._invitation_table.get(to_role)
        self._invitation_table[to_role] = (to_role_name, True)
        return self._send(to_role, to_role_name, msg, header)


    def _send_in_session_msg(self, to_role, msg, headers = None):
        log.debug("In _send_in_session_msg: %s", msg)
        headers = headers if headers else {}
        log.debug("In _send for msg: %s", msg)
        to_role_name = self._conversation[to_role]
        headers['conv-msg-type']  = MSG_TYPE.TRANSMIT
        if self._next_control_msg_type == MSG_TYPE.ACCEPT:
            headers['conv-msg-type']  = headers.get('conv-msg-type', 0) | MSG_TYPE.ACCEPT
            self._next_control_msg_type = 0
        return self._send(to_role, to_role_name, msg, headers)

    def _build_conv_header(self, headers, to_role):
        headers['sender-role'] = self._self_role
        headers['receiver-role'] = to_role
        headers['protocol'] = self._conversation.protocol
        headers['conv-id'] = self._conversation.id
        return headers

    def _send(self, to_role, to_role_name, msg, headers = None):
        headers = headers if headers else {}
        headers = self._build_conv_header(headers, to_role)
        return self._end_point_unit._message_send(msg, headers)


    def _msg_received(self, msg, headers):
        control_msg_type = get_control_msg_type(headers)
        in_session_msg_type = get_in_session_msg_type(headers)
        sender_role = headers['sender-role']
        if control_msg_type == MSG_TYPE.ACCEPT or control_msg_type == MSG_TYPE.INVITE:
            self._conversation[sender_role] = headers['sender-name']
            if control_msg_type == MSG_TYPE.INVITE:
                self.inviter_role = sender_role

                #Note that if the message type is invite you need to accept it,
                #conversation endpoint is an endpoint that is in a conevrsation. Only
                #principals can accept/reject
                #@TODO: really need FSM mechanism here, optherwise it is so ugly :(
                self._next_control_msg_type = MSG_TYPE.ACCEPT
        elif control_msg_type == MSG_TYPE.REJECT:
            exception_msg = 'Invitation rejected by role %s on address %s'\
                            %(headers['sender-role'], headers['reply-to'])
            log.exception(exception_msg)
            raise ConversationError(exception_msg)

        if in_session_msg_type == MSG_TYPE.TRANSMIT:
            pass




class Participant(object):

    def __init__(self, name):
        self._name = name
        self._conversation_end_points = {}
        self._recv_queue = gqueue.Queue()

    @property
    def name(self):
        return self._name


    def start_conversation_endpoint(self, protocol, role, end_point_unit, conversation_id = None):

        convo_id = conversation_id if conversation_id else end_point_unit._build_conv_id()
        c = Conversation(protocol, cid=convo_id)
        conv_endpoint = ConversationEndpoint(end_point_unit)
        conv_endpoint.join(role, c, True)
        self._conversation_end_points[c.id] = conv_endpoint
        return conv_endpoint

    def end_conversation_endpoint(self, conversation_endpoint):
        if conversation_endpoint.get_conversation_id() is not None:
            del self._conversation_end_points[conversation_endpoint.get_conversation_id()]
        return

    def get_conversation_endpoint(self, id):
        if self._conversation_end_points.has_key(id):
            return self._conversation_end_points[id]
        return None

    def get_invitation(self, protocol = None):
        log.debug('Wait to get an invitation')
        return self._recv_queue.get() # this returns a conversations

    def accept_invitation(self, invitation, end_point_unit, merge_with_first_send = False):
        (c, msg, header) =  invitation
        conv_endpoint = ConversationEndpoint(end_point_unit)
        conv_endpoint.accept(msg, header, c, merge_with_first_send)
        self._conversation_end_points[c.id] = conv_endpoint
        log.debug("""\n
        ----------------Accepting invitation:-----------------------------------------------
        Header is: =%s  \n
        ----------------------------------------------------------------------------------
        """, header)
        return conv_endpoint

    def accept_next_invitation(self, end_point_unit, merge_with_first_send = False):
        invitation = self.get_invitation()
        return self.accept_invitation(invitation, end_point_unit, merge_with_first_send)

    def receive_invitation(self, msg, header):
        control_msg_type = get_control_msg_type(header)
        if control_msg_type == MSG_TYPE.INVITE:
            c = Conversation(header['protocol'], header['conv-id'])
            log.debug('_accept_invitation: Conversation added to the list')
            self._recv_queue.put((c, msg, header))


    def reject_invitation(self, msg, headers):
        pass


#######################################################################################################################
# OOI specific (Container Specific) conversations
#######################################################################################################################


#TODO - this may ultimately me loaded from ConversationType Resouce object
class RPCConversationType(object):
    def __init__(self, protocol = None, server_role = None, client_role = None):
        self.protocol = protocol or 'rpc'
        self.server_role = server_role or 'provider'
        self.client_role = client_role or 'requester'

############

class RPCRequesterEndpointUnit(ProcessRPCRequestEndpointUnit):

    def __init__(self, **kwargs):
        ProcessRPCRequestEndpointUnit.__init__(self, **kwargs)

    @property
    def participant(self):
        return self._endpoint._participant

    @property
    def conv_type(self):
        return self._endpoint._conv_type

    def _message_send(self, msg, headers=None, **kwargs):
        return ProcessRPCRequestEndpointUnit.send(self, msg, headers,  **kwargs)

    #Overridden method to hook into message received process
    def _get_response(self, conv_id, timeout):
        result_data, result_headers = ProcessRPCRequestEndpointUnit._get_response(self, conv_id, timeout)

        if 'conv-msg-type' in result_headers:
            c = self.participant.get_conversation_endpoint(conv_id)
            if c:
                c._msg_received( result_data, result_headers)

        return result_data, result_headers

    #Overridden method to hook into message sending process
    def send(self, msg, headers=None, **kwargs):

        convo_id = headers['conv-id'] if 'conv-id' in headers else None

        c = self.participant.start_conversation_endpoint(self.conv_type.protocol, self.conv_type.client_role, self, convo_id)

        c.invite(self.conv_type.server_role, self._endpoint._send_name, merge_with_first_send = True)
        result_data, result_headers = c.send(self.conv_type.server_role, msg, headers)

        c = self.participant.get_conversation_endpoint(convo_id)
        if c:
            self.participant.end_conversation_endpoint(c)

        return result_data, result_headers



class ConversationRPCClient(ProcessRPCClient):
    endpoint_unit_type = RPCRequesterEndpointUnit

    def __init__(self, **kwargs):
        ProcessRPCClient.__init__(self, **kwargs)
        self._conv_type = RPCConversationType()

        if hasattr(self._process, 'name'):
            self._participant = Participant(self._process.name)
        else:
            self._participant = Participant(self._send_name)



    def create_endpoint(self, to_name=None, existing_channel=None, **kwargs):
        return ProcessRPCClient.create_endpoint(self, to_name, existing_channel, **kwargs)


###############


class RPCProviderEndpointUnit(ProcessRPCResponseEndpointUnit):

    def __init__(self, **kwargs):
        ProcessRPCResponseEndpointUnit.__init__(self, **kwargs)

    @property
    def participant(self):
        return self._endpoint._participant

    @property
    def conv_type(self):
        return self._endpoint._conv_type

    #Overridden method to hook into message received process
    def message_received(self, msg, headers):

        #Try to be backward compatiable with non conversation endpoints
        if 'conv-msg-type' in headers:
            self.participant.receive_invitation(msg, headers)
            #TODO = reject an invitation is not supported yet
            self.participant.accept_next_invitation(self, merge_with_first_send = True)

        result, response_headers = ProcessRPCResponseEndpointUnit.message_received(self, msg, headers)

        return result, response_headers

    #Overridden method to hook into message sending process
    def send(self, msg, headers=None, **kwargs):

        c = self.participant.get_conversation_endpoint(headers['conv-id'])
        if c:
            c.send(self.conv_type.client_role, msg, headers)
            self.participant.end_conversation_endpoint(c)
        else:
            #Try to be backward compatiable with non conversation endpoints
            ProcessRPCResponseEndpointUnit.send(self, msg, headers,  **kwargs)

    def _message_send(self, msg, headers=None, **kwargs):
        return ProcessRPCResponseEndpointUnit.send(self, msg, headers,  **kwargs)


class ConversationRPCServer(ProcessRPCServer):
    endpoint_unit_type = RPCProviderEndpointUnit

    def __init__(self, **kwargs):
        ProcessRPCServer.__init__(self, **kwargs)
        self._conv_type = RPCConversationType()
        if hasattr(self._process, 'name'):
            self._participant = Participant(self._process.name)
        else:
            self._participant = Participant(self._recv_name)


    def create_endpoint(self, **kwargs):
        return ProcessRPCServer.create_endpoint(self, **kwargs)
