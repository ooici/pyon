#!/usr/bin/env python

"""ION messaging endpoints"""
from pyon.util import log

__author__ = 'Michael Meisinger, David Stuebe, Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.net.endpoint import Publisher, Subscriber, EndpointUnit, process_interceptors, RPCRequestEndpointUnit, BaseEndpoint, RPCClient, RPCResponseEndpointUnit, RPCServer
from pyon.util.log import log


#############################################################################
# PROCESS LEVEL ENDPOINTS
#############################################################################

class ProcessEndpointUnitMixin(EndpointUnit):
    """
    Common-base mixin for Process related endpoints.

    This reduces code duplication on either side of the ProcessRPCRequest/ProcessRPCResponse.
    """
    def __init__(self, process=None, **kwargs):
        EndpointUnit.__init__(self, **kwargs)
        self._process = process

    def _build_invocation(self, **kwargs):
        newkwargs = kwargs.copy()
        newkwargs.update({'process':self._process})

        inv = EndpointUnit._build_invocation(self, **newkwargs)
        return inv

    def _intercept_msg_in(self, inv):
        """
        Override for incoming message interception.

        This is a request, so the order should be Message, Process
        """
        inv_one = EndpointUnit._intercept_msg_in(self, inv)
        inv_two = process_interceptors(self.interceptors["process_incoming"] if "process_incoming" in self.interceptors else [], inv_one)
        return inv_two

    def _intercept_msg_out(self, inv):
        """
        Override for outgoing message interception.

        This is request, so the order should be Process, Message
        """
        inv_one = process_interceptors(self.interceptors["process_outgoing"] if "process_outgoing" in self.interceptors else [], inv)
        inv_two = EndpointUnit._intercept_msg_out(self, inv_one)

        return inv_two

    def _build_header(self, raw_msg):
        """
        Builds the header for this Process-level RPC conversation.
        https://confluence.oceanobservatories.org/display/syseng/CIAD+COI+OV+Common+Message+Format
        """

        header = EndpointUnit._build_header(self, raw_msg)

        # add our process identity to the headers
        header.update({'sender-name'  : self._process.name or 'unnamed-process',     # @TODO
                       'sender'       : self._process.id })

        if hasattr(self._process,'process_type' ):
            header.update({'sender-type'  : self._process.process_type or 'unknown-process-type' })
            if self._process.process_type == 'service':
                header.update({ 'sender-service' : "%s,%s" % ( self.channel._send_name.exchange,self._process.name) })

        context = self._process.get_context()
        log.debug('ProcessEndpointUnitMixin._build_header has context of: %s', context)

        # use context to set security attributes forward
        if isinstance(context, dict):
            # fwd on actor specific information, according to common message format spec
            actor_id            = context.get('ion-actor-id', None)
            actor_roles         = context.get('ion-actor-roles', None)
            actor_tokens        = context.get('ion-actor-tokens', None)
            expiry              = context.get('expiry', None)
            container_id        = context.get('origin-container-id', None)

            #If an actor-id is specified then there may be other associated data that needs to be passed on
            if actor_id:
                header['ion-actor-id']  = actor_id
                if actor_roles:     header['ion-actor-roles']   = actor_roles
                if actor_tokens:    header['ion-actor-tokens']  = actor_tokens

            if expiry:          header['expiry']                = expiry
            if container_id:    header['origin-container-id']   = container_id
        else:
            # no context? we're the originator of the message then
            container_id                    = BaseEndpoint._get_container_instance().id
            header['origin-container-id']   = container_id

        return header

    def _get_sample_name(self):
        return str(self._process.id)

    def _get_sflow_manager(self):
        return self._process.container.sflow_manager

class ProcessRPCRequestEndpointUnit(ProcessEndpointUnitMixin, RPCRequestEndpointUnit):
    def __init__(self, process=None, **kwargs):
        ProcessEndpointUnitMixin.__init__(self, process=process)
        RPCRequestEndpointUnit.__init__(self, **kwargs)

    def _build_header(self, raw_msg):
        """
        Override to direct the calls in _build_header - first the RPCRequest side, then the Process mixin.
        """

        header1 = RPCRequestEndpointUnit._build_header(self, raw_msg)
        header2 = ProcessEndpointUnitMixin._build_header(self, raw_msg)

        header1.update(header2)

        return header1

class ProcessRPCClient(RPCClient):
    endpoint_unit_type = ProcessRPCRequestEndpointUnit

    def __init__(self, process=None, **kwargs):
        self._process = process
        RPCClient.__init__(self, **kwargs)

    def create_endpoint(self, to_name=None, existing_channel=None, **kwargs):
        if not self._process:
            raise StandardError("No Process specified")

        newkwargs = kwargs.copy()
        newkwargs['process'] = self._process
        return RPCClient.create_endpoint(self, to_name, existing_channel, **newkwargs)


class ProcessRPCResponseEndpointUnit(ProcessEndpointUnitMixin, RPCResponseEndpointUnit):
    def __init__(self, process=None, routing_call=None, **kwargs):
        ProcessEndpointUnitMixin.__init__(self, process=process)
        RPCResponseEndpointUnit.__init__(self, **kwargs)
        self._routing_call = routing_call

    def _message_received(self, msg, headers):
        """
        Message received override.

        Sets the process' context here to be picked up by subsequent calls out by this service to other services, or replies.
        """
        ######
        ###### THIS IS WHERE THE THREAD LOCAL HEADERS CONTEXT IS SET ######
        ######

        # With the property _routing_call set, as is the case 95% of the time in the Process-level endpoints,
        # we have to set the call context from the ION process' calling greenlet, as context is greenlet-specific.
        # This is done in the _make_routing_call override here, passing it the context to be set.
        # See also IonProcessThread._control_flow.

        with self._process.push_context(headers):
            return RPCResponseEndpointUnit._message_received(self, msg, headers)

    def _build_header(self, raw_msg):
        """
        Override to direct the calls in _build_header - first the RPCResponse side, then the Process mixin.
        """

        header1 = RPCResponseEndpointUnit._build_header(self, raw_msg)
        header2 = ProcessEndpointUnitMixin._build_header(self, raw_msg)

        header1.update(header2)

        return header1

    def _make_routing_call(self, call, op_args):
        if not self._routing_call:
            return RPCResponseEndpointUnit._make_routing_call(self, call, op_args)

        ar = self._routing_call(call, op_args, context=self._process.get_context())
        return ar.get()     # @TODO: timeout?


class ProcessRPCServer(RPCServer):
    endpoint_unit_type = ProcessRPCResponseEndpointUnit

    def __init__(self, process=None, routing_call=None, **kwargs):
        assert process
        self._process = process
        self._routing_call = routing_call
        RPCServer.__init__(self, **kwargs)

    @property
    def routing_call(self):
        return self._routing_call

    @routing_call.setter
    def routing_call(self, value):
        self._routing_call = value

    def create_endpoint(self, **kwargs):
        newkwargs = kwargs.copy()
        newkwargs['process'] = self._process
        newkwargs['routing_call'] = self._routing_call
        return RPCServer.create_endpoint(self, **newkwargs)



class ProcessPublisher(Publisher):
    def __init__(self, process=None, **kwargs):
        self._process = process
        Publisher.__init__(self, **kwargs)


class PublisherError(StandardError):
    """
    An exception class for errors in the subscriber
    """




class SubscriberError(StandardError):
    """
    An exception class for errors in the subscriber
    """


class ProcessSubscriber(Subscriber):
    def __init__(self, process=None, **kwargs):
        self._process = process
        Subscriber.__init__(self, **kwargs)


