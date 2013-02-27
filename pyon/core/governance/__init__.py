
'''
This module file contains Governance related constants and helper functions used within the Container.
'''
from pyon.core import bootstrap
from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest, Inconsistent
from pyon.ion.resource import RT, PRED, LCS, OT
from pyon.util.containers import get_ion_ts, get_safe
from pyon.util.log import log

#These constants are ubiquitous, so define in the container
DEFAULT_ACTOR_ID = 'anonymous'
ORG_MANAGER_ROLE = 'ORG_MANAGER'  # Can only act upon resource within the specific Org
ORG_MEMBER_ROLE = 'ORG_MEMBER'    # Can only access resources within the specific Org
ION_MANAGER = 'ION_MANAGER'   # Can act upon resources across all Orgs - like a Super User access


#Helper methods

def get_role_message_headers(org_roles):
    '''
    Iterate the Org(s) that the user belongs to and create a header that lists only the role names per Org assigned
    to the user; i.e. {'ION': ['Member', 'Operator'], 'Org2': ['Member']}
    @param org_roles:
    @return:
    '''
    role_header = dict()
    try:
        for org in org_roles:
            role_header[org] = []
            for role in org_roles[org]:
                role_header[org].append(role.name)
        return role_header

    except Exception, e:
        log.error(e)
        return role_header


def build_actor_header(actor_id=DEFAULT_ACTOR_ID, actor_roles=None):
    '''
    Use this to build the message header used by governance to identify the actor and roles.
    @param actor_id:
    @param actor_roles:
    @return:
    '''
    actor_roles = actor_roles or {}
    return {'ion-actor-id': actor_id, 'ion-actor-roles': actor_roles }

def get_actor_header(actor_id):
    '''
    Returns the actor related message headers for a specific actor_id - will return anonymous if the actor_id is not found.
    @param actor_id:
    @return:
    '''
    actor_header = build_actor_header(DEFAULT_ACTOR_ID, {})

    if actor_id:
        try:
            header_roles = find_roles_by_actor(actor_id)
            actor_header = build_actor_header(actor_id, header_roles)
        except Exception, e:
            log.error(e)

    return actor_header

def has_org_role(role_header=None, org_name=None, role_name=None):
    '''
    Check the ion-actor-roles message header to see if this actor has the specified role in the specified Org.
    Parameter role_name can be a string with the name of a user role or a list of user role names, which will
    recursively call this same method for each role name in the list until one is found or the list is exhausted.
    @param role_header:
    @param org_name:
    @param role_name:
    @return:
    '''
    if role_header is None or org_name is None or role_name is None:
        raise BadRequest("One of the parameters to this method are not set")

    if isinstance(role_name, list):
        for role in role_name:
            if has_org_role(role_header, org_name, role):
                return True
    else:
        if role_header.has_key(org_name):
            if role_name in role_header[org_name]:
                return True

    return False


def find_roles_by_actor(actor_id=None):
    '''
    Returns a dict of all User Roles roles by Org Name associated with the specified actor
    @param actor_id:
    @return:
    '''
    if actor_id is None or not len(actor_id):
        raise BadRequest("The actor_id parameter is missing")

    role_dict = dict()

    gov_controller = bootstrap.container_instance.governance_controller
    role_list,_ = gov_controller.rr.find_objects(actor_id, PRED.hasRole, RT.UserRole)

    for role in role_list:

        if not role_dict.has_key(role.org_name):
            role_dict[role.org_name] = list()

        role_dict[role.org_name].append(role.name)

    #Membership in ION Org is implied
    if not role_dict.has_key(gov_controller.system_root_org_name):
        role_dict[gov_controller.system_root_org_name] = list()

    role_dict[gov_controller.system_root_org_name].append(ORG_MEMBER_ROLE)


    return role_dict


def get_system_actor():
    '''
    Returns the ION System Actor defined in the Resource Registry
    @return:
    '''
    try:
        gov_controller = bootstrap.container_instance.governance_controller
        system_actor, _ = gov_controller.rr.find_resources(RT.ActorIdentity,name=get_safe(gov_controller.CFG, "system.system_actor", "ionsystem"), id_only=False)
        if not system_actor:
            return None

        return system_actor[0]

    except Exception, e:
        log.error(e)
        return None

def is_system_actor(actor_id):
    '''
    Is this the specified actor_id the system actor
    @param actor_id:
    @return:
    '''
    system_actor = get_system_actor()
    if system_actor is not None and system_actor._id == actor_id:
        return True

    return False

def get_system_actor_header(system_actor=None):
    '''
    Returns the actor related message headers for a the ION System Actor
    @param system_actor:
    @return:
    '''
    try:
        if system_actor is None:
            system_actor = get_system_actor()

        if not system_actor or system_actor is None:
            log.warn('The ION System Actor Identity was not found; defaulting to anonymous actor')
            actor_header = get_actor_header(None)
        else:
            actor_header = get_actor_header(system_actor._id)

        return actor_header

    except Exception, e:
        log.error(e)
        return get_actor_header(None)


def get_resource_commitments(actor_id, resource_id):
    '''
    Returns the list of commitments for the specified user and resource
    @param actor_id:
    @param resource_id:
    @return:
    '''
    log.debug("Finding commitments for actor_id: %s and resource_id: %s" % (actor_id, resource_id))

    try:
        gov_controller = bootstrap.container_instance.governance_controller
        commitments,_ = gov_controller.rr.find_objects(resource_id, PRED.hasCommitment, RT.Commitment)
        if not commitments:
            return None

        cur_time = int(get_ion_ts())
        commitment_list = []
        for com in commitments:  #TODO - update when Retired is removed from find_objects
            if com.consumer == actor_id and com.lcstate != LCS.RETIRED and ( com.expiration == 0 or\
                                                                             ( com.expiration > 0 and cur_time < com.expiration)):
                commitment_list.append(com)

        if commitment_list:
            return commitment_list

    except Exception, e:
        log.error(e)

    return None

def has_resource_commitments(actor_id, resource_id):
    '''
    Returns a ResourceCommitmentStatus object indicating the commitment status between this resource/actor
    Can only have an exclusive commitment if actor already has a shared commitment.
    @param actor_id:
    @param resource_id:
    @return:
    '''
    ret_status = IonObject(OT.ResourceCommitmentStatus)
    commitments = get_resource_commitments(actor_id, resource_id)
    if commitments is None:
        #No commitments were found between this resource_id and actor_id
        return ret_status

    ret_status.shared = True

    for com in commitments:
        if com.commitment.exclusive == True:
            #Found an exclusive commitment
            ret_status.exclusive = True
            return ret_status

    #Only a shared commitment was found
    return ret_status


def has_shared_resource_commitment(actor_id=None, resource_id=None):
    '''
    This method returns True if the specified actor_id has acquired shared access for the specified resource id, otherwise False.
    @param msg:
    @param headers:
    @return:
    '''
    if actor_id is None or resource_id is None:
        raise BadRequest('One or all of the method parameters are not set')

    commitment_status =  has_resource_commitments(actor_id, resource_id)

    return commitment_status.shared


def has_exclusive_resource_commitment(actor_id=None, resource_id=None):
    '''
    This method returns True if the specified actor_id has acquired exclusive access for the specified resource id, otherwise False.
    @param msg:
    @param headers:
    @return:
    '''
    if actor_id is None or resource_id is None:
        raise BadRequest('One or all of the method parameters are not set')

    commitment_status =  has_resource_commitments(actor_id, resource_id)

    #If the resource has not been acquired for sharing, then it can't have been acquired exclusively
    if not commitment_status.shared:
        return False

    return commitment_status.exclusive

def is_resource_owner(actor_id=None, resource_id=None):
    '''
    Returns True if the specified actor_id is an Owner of the specified resource id, otherwise False
    @param actor_id:
    @param resource_id:
    @return:
    '''
    if actor_id is None or resource_id is None:
        raise BadRequest('One or all of the method parameters are not set')

    gov_controller = bootstrap.container_instance.governance_controller
    owners =  gov_controller.rr.find_objects(subject=resource_id, predicate=PRED.hasOwner, object_type=RT.ActorIdentity, id_only=True)

    if actor_id not in owners[0]:
        return False

    return True




class GovernanceHeaderValues(object):
    '''
    A helper class for containing governance values from a message header
    '''

    def __init__(self, headers, resource_id_required=True):
        '''
        A helper object for retrieving governance related values: op, actor_id, actor_roles, resource_id from the message header
        @param headers:
        @param resource_id_required: True if the message header must have a resource-id field and value.
        @return op, actor_id, actor_roles, resource_id:
        '''

        if not headers or not isinstance(headers, dict) or not len(headers):
            raise BadRequest('The headers parameter is not a valid message header dictionary')

        if headers.has_key('op'):
            self._op = headers['op']
        else:
            self._op = "Unknown-Operation"

        if headers.has_key('process'):
            if getattr(headers['process'],'name'):
                self._process_name = headers['process'].name
            else:
                self._process_name = "Unknown-Process"
        else:
            self._process_name = "Unknown-Process"


        #The self.name references below should be provided by the running ION process ( service, agent, etc ) which will be using this class.
        if headers.has_key('ion-actor-id'):
            self._actor_id = headers['ion-actor-id']
        else:
            raise Inconsistent('%s(%s) has been denied since the ion-actor-id can not be found in the message headers'% (self._process_name, self._op))

        if headers.has_key('ion-actor-roles'):
            self._actor_roles = headers['ion-actor-roles']
        else:
            raise Inconsistent('%s(%s) has been denied since the ion-actor-roles can not be found in the message headers'% (self._process_name, self._op))

        if headers.has_key('resource-id'):
            self._resource_id = headers['resource-id']
        else:
            if resource_id_required:
                raise Inconsistent('%s(%s) has been denied since the resource-id can not be found in the message headers'% (self._process_name, self._op))
            self._resource_id = ''

    @property
    def op(self):
        return self._op

    @property
    def actor_id(self):
        return self._actor_id

    @property
    def actor_roles(self):
        return self._actor_roles

    @property
    def resource_id(self):
        return self._resource_id

    @property
    def process_name(self):
        return self._process_name

