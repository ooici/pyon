#!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

import copy
import datetime
import string


from pyon.core.bootstrap import IonObject
from pyon.core.registry import issubtype
from pyon.core.exception import  Inconsistent, NotFound, BadRequest
from pyon.ion.resource import RT, PRED, OT
from interface.objects import ProposalStatusEnum, NegotiationTypeEnum, ProposalOriginatorEnum, NegotiationStatusEnum


class Negotiation(object):

    #Clones the most recent proposal and modifies conditions as needed
    @classmethod
    def create_counter_proposal(self,negotiation=None, proposal_status=ProposalStatusEnum.COUNTER,
                                originator=ProposalOriginatorEnum.CONSUMER):

        if negotiation is None or negotiation.type_ != RT.Negotiation:
            raise BadRequest('The negotiation parameter must be a valid Negotiation object')

        counter_sap = copy.deepcopy(negotiation.proposals[-1])

        counter_sap.sequence_num += 1
        counter_sap.proposal_status = proposal_status
        counter_sap.originator = originator

        return counter_sap

    def __init__(self,serv_prov, negotiation_rules=None):

        self.service_provider = serv_prov

        if negotiation_rules is None:
            self.negotiation_rules = {}
        else:
            self.negotiation_rules = negotiation_rules


    def read_negotiation(self, sap=None):

        if sap is None or ( sap.type_ != OT.ServiceAgreementProposal and not issubtype(sap.type_, OT.ServiceAgreementProposal)):
            raise BadRequest('The sap parameter must be a valid Service Agreement Proposal object')

        if not sap.negotiation_id:
            raise BadRequest('The Service Agreement Proposal object (sap) is missing a negotiation_id value')

        neg_obj = self.service_provider.clients.resource_registry.read(sap.negotiation_id)

        return neg_obj


    def create_negotiation(self, sap=None):

        if sap is None or ( sap.type_ != OT.ServiceAgreementProposal and not issubtype(sap.type_, OT.ServiceAgreementProposal)):
            raise BadRequest('The sap parameter must be a valid Service Agreement Proposal object')

        if sap.proposal_status != ProposalStatusEnum.INITIAL or sap.sequence_num != 0:
            raise Inconsistent('The specified Service Agreement Proposal has inconsistent status fields')

        if sap.negotiation_id != '':
            raise Inconsistent('The specified Service Agreement Proposal cannot have a negotiation_id for an initial proposal')

        if self.negotiation_rules.has_key(sap.type_):
            #validate preconditions before creating
            for pc in self.negotiation_rules[sap.type_]['pre_conditions']:
                if pc.startswith('not '):
                    pre_condition_met = not eval("self.service_provider." + pc.lstrip('not ')) #Strip off the 'not ' part
                else:
                    pre_condition_met = eval("self.service_provider."+pc)

                if not pre_condition_met:
                    raise BadRequest("A precondition for this request has not been satisfied: %s" % pc)

        #Should be able to determine the negotiation type based on the intial originator
        neg_type = NegotiationTypeEnum.REQUEST
        if sap.originator == ProposalOriginatorEnum.PROVIDER:
            neg_type = NegotiationTypeEnum.INVITATION
        elif sap.originator == ProposalOriginatorEnum.BROKER:
            neg_type = NegotiationTypeEnum.BROKERED

        neg_obj = IonObject(RT.Negotiation, negotiation_type=neg_type)

        #If there is a description in the initial proposal, then set the negotiation description with it.
        if sap.description != '':
            neg_obj.description = sap.description

        neg_id,_ = self.service_provider.clients.resource_registry.create(neg_obj)

        #Create associations between the parties
        self.service_provider.clients.resource_registry.create_association(sap.consumer, PRED.hasNegotiation, neg_id)
        self.service_provider.clients.resource_registry.create_association(sap.provider, PRED.hasNegotiation, neg_id)
        if sap.broker != "":
            self.service_provider.clients.resource_registry.create_association(sap.broker, PRED.hasNegotiation, neg_id)


        return neg_id

    def update_negotiation(self, sap=None, reason=None):

        #Find the Negotiation resource associated with this proposal
        if sap is None or sap.negotiation_id == '':
            raise Inconsistent('The Service Agreement Proposal must have a negotiation resource id associated with it')

        neg_obj = self.service_provider.clients.resource_registry.read(sap.negotiation_id)

        if sap.sequence_num != len(neg_obj.proposals):
            raise Inconsistent('The Service Agreement Proposal does not have the correct sequence_num value (%d) for this negotiation (%d)' % (sap.sequence_num, len(neg_obj.proposals)))


        #Synchronize negotiation status based on proposals
        if sap.proposal_status == ProposalStatusEnum.REJECTED:
            neg_obj.negotiation_status = NegotiationStatusEnum.REJECTED
        elif sap.proposal_status == ProposalStatusEnum.ACCEPTED:
            #Look for an previously Accepted proposal from the other party
            for prop in neg_obj.proposals:
                if prop.proposal_status == ProposalStatusEnum.ACCEPTED and prop.originator != sap.originator:
                    neg_obj.negotiation_status = NegotiationStatusEnum.ACCEPTED

        if reason is not None:
            neg_obj.reason = reason

        #Add the current proposal to the Negotiation object to keep a record of it - then save it
        neg_obj.proposals.append(sap)

        neg_id,_ = self.service_provider.clients.resource_registry.update(neg_obj)

        self._publish_status_event(neg_obj)

        if neg_obj.negotiation_status == NegotiationStatusEnum.ACCEPTED:
            self._execute_accept_action(neg_obj.proposals[-1])
            #Publish request granted notification
            self._publish_status_event(neg_obj, ProposalStatusEnum.GRANTED)


        return neg_id


    def _execute_accept_action(self, sap):

        if self.negotiation_rules.has_key(sap.type_):
            action = self.negotiation_rules[sap.type_]['accept_action']
            action_result = eval("self.service_provider."+action)

            return action_result

        return None

    def _publish_status_event(self, negotiation, status=None):
        #Sent request opened event

        #Get lastest proposal
        sap = negotiation.proposals[-1]

        event_type =   string.rstrip(sap.type_,'Proposal') + 'NegotiationStatusEvent'

        #Thw negotiation id will be used for the orgin
        origin = negotiation._id

        event_data = dict()
        event_data['origin_type'] = RT.Negotiation
        event_data['originator'] = sap.originator

        if status is None:
            event_data['sub_type'] = sap.proposal_status
            event_data['description'] = ProposalStatusEnum._str_map[sap.proposal_status]
        else:
            event_data['sub_type'] = status
            event_data['description'] = ProposalStatusEnum._str_map[status]

        #Look for other data that belongs in the event
        for field in sap._schema:
            for decorator in sap._schema[field]['decorators']:
                if decorator == 'EventData':
                    event_data[field] = getattr(sap,field)


        self.service_provider.event_pub.publish_event(event_type=event_type,
            origin=origin, **event_data)


