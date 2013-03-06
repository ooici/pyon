
#!/usr/bin/env python

__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'


from pyon.util.unit_test import PyonTestCase
from mock import Mock
from nose.plugins.attrib import attr
from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest, Inconsistent
from pyon.core.governance.negotiation import Negotiation
from pyon.ion.resource import RT, PRED, OT
from interface.objects import ProposalStatusEnum, NegotiationTypeEnum, ProposalOriginatorEnum, NegotiationStatusEnum


@attr('UNIT')
class NegotiationTest(PyonTestCase):


    def setUp(self):

        self.clients = Mock()

        self.mock_create = self.clients.resource_registry.create
        self.mock_read = self.clients.resource_registry.read
        self.mock_update = self.clients.resource_registry.update
        self.mock_delete = self.clients.resource_registry.delete
        self.mock_create_association = self.clients.resource_registry.create_association
        self.mock_delete_association = self.clients.resource_registry.delete_association
        self.mock_find_objects = self.clients.resource_registry.find_objects
        self.mock_find_resources = self.clients.resource_registry.find_resources
        self.mock_find_subjects = self.clients.resource_registry.find_subjects

        self.actor_identity = Mock()
        self.actor_identity._id = '111'
        self.actor_identity.name = "Test User"

        self.org = Mock()
        self.org._id = '222'
        self.org.name = "Org2"

        self.event_pub = Mock()

        #Mmock objects to simulate helper methods
        self.preconditions = Mock()
        self.accept_actions = Mock()



    def test_read_negotiation(self):

        negotiation_handler = Negotiation(self)

        with self.assertRaises(BadRequest) as cm:
            negotiation_handler.read_negotiation()
        self.assertIn('The sap parameter must be a valid Service Agreement Proposal object',cm.exception.message)

        sap = IonObject(OT.EnrollmentProposal,consumer=self.actor_identity._id, provider=self.org._id )

        with self.assertRaises(BadRequest) as cm:
            negotiation_handler.read_negotiation(sap)
        self.assertIn('The Service Agreement Proposal object (sap) is missing a negotiation_id value',cm.exception.message)

        negotiation = Mock()
        negotiation._id = '456'

        sap.negotiation_id = negotiation._id

        self.mock_read.return_value = negotiation

        neg_obj = negotiation_handler.read_negotiation(sap)

        self.assertEqual(neg_obj, negotiation)



    def test_create_counter_proposal(self):

        with self.assertRaises(BadRequest) as cm:
            consumer_accept_sap = Negotiation.create_counter_proposal(proposal_status=ProposalStatusEnum.INITIAL)
        self.assertIn('The negotiation parameter must be a valid Negotiation object',cm.exception.message)

        negotiation_handler = Negotiation(self)

        sap = IonObject(OT.EnrollmentProposal,consumer=self.actor_identity._id, provider=self.org._id )

        negotiation = Mock()
        negotiation._id = '456'
        negotiation.type_ = RT.Negotiation
        negotiation.proposals = [sap]

        self.mock_read.return_value = negotiation
        self.mock_create.return_value = ['456', 2]

        neg_id = negotiation_handler.create_negotiation(sap)

        sap.negotiation_id = neg_id

        consumer_accept_sap = Negotiation.create_counter_proposal(negotiation, proposal_status=ProposalStatusEnum.COUNTER,
                originator=ProposalOriginatorEnum.PROVIDER)

        self.assertEqual(consumer_accept_sap.negotiation_id, negotiation._id)
        self.assertEqual(len(negotiation.proposals),1)
        self.assertEqual(consumer_accept_sap.sequence_num, len(negotiation.proposals))
        self.assertEqual(consumer_accept_sap.proposal_status, ProposalStatusEnum.COUNTER)
        self.assertEqual(consumer_accept_sap.originator, ProposalOriginatorEnum.PROVIDER)



    def test_create_negotiation(self):

        self.preconditions.check_method1.return_value = True
        self.preconditions.check_method2.return_value = False
        self.accept_actions.accept_method.return_value = None

        negotiation_rules = {
            OT.EnrollmentProposal: {
                'pre_conditions': ['preconditions.check_method1(sap.consumer)', 'not preconditions.check_method2(sap.provider,sap.consumer)'],
                'accept_action': 'accept_actions.accept_method(sap.provider,sap.consumer)'
            }}

        negotiation_handler = Negotiation(self, negotiation_rules)

        with self.assertRaises(BadRequest) as cm:
            negotiation_handler.create_negotiation()
        self.assertIn('The sap parameter must be a valid Service Agreement Proposal object',cm.exception.message)

        sap = IonObject(OT.EnrollmentProposal,consumer=self.actor_identity._id, provider=self.org._id )
        sap.sequence_num = 1  #Force an error
        with self.assertRaises(Inconsistent) as cm:
            negotiation_handler.create_negotiation(sap)
        self.assertIn('The specified Service Agreement Proposal has inconsistent status fields',cm.exception.message)

        sap = IonObject(OT.EnrollmentProposal,consumer=self.actor_identity._id, provider=self.org._id )
        sap.proposal_status = ProposalStatusEnum.COUNTER  #Force an error
        with self.assertRaises(Inconsistent) as cm:
            negotiation_handler.create_negotiation(sap)
        self.assertIn('The specified Service Agreement Proposal has inconsistent status fields',cm.exception.message)

        sap = IonObject(OT.EnrollmentProposal,consumer=self.actor_identity._id, provider=self.org._id )
        sap.negotiation_id = 'efefeff'  #Force an error
        with self.assertRaises(Inconsistent) as cm:
            negotiation_handler.create_negotiation(sap)
        self.assertIn('The specified Service Agreement Proposal cannot have a negotiation_id for an initial proposal',cm.exception.message)

        sap = IonObject(OT.EnrollmentProposal,consumer=self.actor_identity._id, provider=self.org._id )

        negotiation = Mock()
        negotiation._id = '456'
        negotiation.type_ = RT.Negotiation
        negotiation.proposals = []

        self.mock_read.return_value = negotiation
        self.mock_create.return_value = ['456', 2]

        neg_id = negotiation_handler.create_negotiation(sap)

        self.assertEqual(neg_id, negotiation._id)
        self.assertEqual(len(negotiation.proposals),0)

        self.assertEqual(self.preconditions.check_method1.called,True)
        self.assertEqual(self.preconditions.check_method2.called,True)
        self.assertEqual(self.accept_actions.accept_method.called,False)


    def test_create_negotiation_fail_precondition(self):

        self.preconditions.check_method1.return_value = False
        self.accept_actions.accept_method.return_value = None

        negotiation_rules = {
            OT.EnrollmentProposal: {
                'pre_conditions': ['preconditions.check_method1(sap.consumer)', 'not preconditions.check_method2(sap.provider,sap.consumer)'],
                'accept_action': 'accept_actions.accept_method(sap.provider,sap.consumer)'
            }}
        negotiation_handler = Negotiation(self, negotiation_rules)


        sap = IonObject(OT.EnrollmentProposal,consumer=self.actor_identity._id, provider=self.org._id )

        negotiation = Mock()
        negotiation._id = '456'
        negotiation.type_ = RT.Negotiation
        negotiation.proposals = []

        self.mock_read.return_value = negotiation
        self.mock_create.return_value = ['456', 2]

        with self.assertRaises(BadRequest) as cm:
            neg_id = negotiation_handler.create_negotiation(sap)
        self.assertIn('A precondition for this request has not been satisfied: preconditions.check_method1(sap.consumer)',cm.exception.message)

        self.assertEqual(len(negotiation.proposals),0)

        self.assertEqual(self.preconditions.check_method1.called,True)
        self.assertEqual(self.preconditions.check_method2.called,False)
        self.assertEqual(self.accept_actions.accept_method.called,False)

    def test_update_negotiation(self):

        self.preconditions.check_method1.return_value = True
        self.preconditions.check_method2.return_value = False
        self.accept_actions.accept_method.return_value = None

        negotiation_rules = {
            OT.EnrollmentProposal: {
                'pre_conditions': ['preconditions.check_method1(sap.consumer)', 'not preconditions.check_method2(sap.provider,sap.consumer)'],
                'accept_action': 'accept_actions.accept_method(sap.provider,sap.consumer)'
            }}

        negotiation_handler = Negotiation(self, negotiation_rules, self.event_pub)

        with self.assertRaises(Inconsistent) as cm:
            negotiation_handler.update_negotiation()
        self.assertIn('The Service Agreement Proposal must have a negotiation resource id associated with it',cm.exception.message)

        sap = IonObject(OT.EnrollmentProposal,consumer=self.actor_identity._id, provider=self.org._id )

        with self.assertRaises(Inconsistent) as cm:
            negotiation_handler.update_negotiation(sap)
        self.assertIn('The Service Agreement Proposal must have a negotiation resource id associated with it',cm.exception.message)

        negotiation = Mock()
        negotiation._id = '456'
        negotiation.type_ = RT.Negotiation
        negotiation.proposals = []

        sap.negotiation_id = negotiation._id

        self.mock_read.return_value = negotiation
        self.mock_update.return_value = ['456', 2]


        neg_id = negotiation_handler.update_negotiation(sap)

        self.assertEqual(self.event_pub.publish_event.called,True)

        self.assertEqual(neg_id, negotiation._id)
        self.assertEqual(len(negotiation.proposals),1)

        counter_sap = Negotiation.create_counter_proposal(negotiation, ProposalStatusEnum.REJECTED, ProposalOriginatorEnum.PROVIDER)

        neg_id = negotiation_handler.update_negotiation(counter_sap, 'Fake rejection reason')

        self.assertEqual(len(negotiation.proposals),2)
        self.assertEqual(negotiation.negotiation_status, NegotiationStatusEnum.REJECTED)
        self.assertEquals(negotiation.reason, 'Fake rejection reason' )

        counter_sap = Negotiation.create_counter_proposal(negotiation, ProposalStatusEnum.ACCEPTED, ProposalOriginatorEnum.PROVIDER)

        neg_id = negotiation_handler.update_negotiation(counter_sap)
        self.assertEqual(len(negotiation.proposals),3)
        self.assertEqual(negotiation.negotiation_status, NegotiationStatusEnum.REJECTED)

        counter_sap = Negotiation.create_counter_proposal(negotiation, ProposalStatusEnum.ACCEPTED, ProposalOriginatorEnum.CONSUMER)

        neg_id = negotiation_handler.update_negotiation(counter_sap)
        self.assertEqual(len(negotiation.proposals),4)
        self.assertEqual(negotiation.negotiation_status, NegotiationStatusEnum.ACCEPTED)

        self.assertEqual(self.accept_actions.accept_method.called,True)