"""
Example service that strives to demonstrate how
to port a service from R1 to R2
"""

from pyon.public import Container
from pyon.core.bootstrap import IonObject
from pyon.net.endpoint import RPCClient

from interface.services.ihello_resource_service import IHelloResourceService, BaseHelloResourceService

ACTIVATE = 0
DEACTIVATE = 1
COMMISSION = 2
DECOMMISSION = 3
RETIRE = 4
DEVELOP = 5

ACTIVE = 0
INACTIVE = 1
COMMISSIONED = 2
DECOMMISSIONED = 3
RETIRED = 4
DEVELOPED =5

class HelloResourceService(BaseHelloResourceService):

    def create_instrument_resource(self, instrument_info={}):
        """
        Creates an InstrumentResource object by:
        1) request InstrumentResource object instance from object registry
        2) configure object instance
        3) call resource registery to persist object
        """

        # Request InstrumentResource instance from object registry
        # and initialize it.  This is comparable to:
        #    resource = yield self.rc.create_instance(INSTRUMENT_RESOURCE_TYPE, ResourceName=name, ResourceDescription='Preposterous instrument resource!')
        #
        #    if request.IsFieldSet('configuration'):
        #
        #        if request.configuration.IsFieldSet('name'):
        #            resource.name = request.configuration.name
        #
        #        if request.configuration.IsFieldSet('make'):
        #            resource.make = request.configuration.make
        #
        #        if request.configuration.IsFieldSet('model'):
        #            resource.model = request.configuration.model
        #
        #        if request.configuration.IsFieldSet('serial_number'):
        #            resource.serial_number = request.configuration.serial_number
        #
        instrument_resource_dict = {}
        instrument_resource_dict["name"] = instrument_info.name
        instrument_resource_dict["make"] = instrument_info.make
        instrument_resource_dict["model"] = instrument_info.model
        instrument_resource_dict["serial_number"] = instrument_info.serial_number

        resource = IonObject("InstrumentResource", instrument_resource_dict)

        # Persist resource.  This is comparable to:
        #    yield self.rc.put_instance(resource)
        create_result = self.clients.resource_registry.create(resource)

        # resource id and revision number are always returned from create
        resource_id, version = create_result

        # Return resouce id.  This is comparable to:
        #    response = yield self.mc.create_instance(MessageContentTypeID = RESOURCE_RESPONSE_TYPE)
        #    response.resource_reference = self.rc.reference_instance(resource)
        #    response.MessageResponseCode = response.ResponseCodes.OK
        #    yield self.reply_ok(msg, response)
        return resource_id


    def update_instrument_resource(self, resource_id='', instrument_info={}):
        """
        Update an InstrumentResource object by:
        1) call resource registry to read object
        2) update object fields
        3) call resource registery to persist updated object
        """

        # Read object.  This is comparable to:
        #    resource = yield self.rc.get_instance(request.resource_reference)
        resource = self.clients.resource_registry.read(resource_id)

        # Update fields.  This is comparable to:
        #    if request.configuration.IsFieldSet('name'):
        #        resource.name = request.configuration.name
        #    else:
        #        resource.ClearField('name')
        #
        #    if request.configuration.IsFieldSet('make'):
        #        resource.make = request.configuration.make
        #    else:
        #        resource.ClearField('make')
        #
        #    if request.configuration.IsFieldSet('model'):
        #        resource.model = request.configuration.model
        #    else:
        #        resource.ClearField('model')
        #
        #    if request.configuration.IsFieldSet('serial_number'):
        #        resource.serial_number = request.configuration.serial_number
        #    else:
        #        resource.ClearField('serial_number')
        resource.name = instrument_info.name
        resource.make = instrument_info.make
        resource.model = instrument_info.model
        resource.serial_number = instrument_info.serial_number

        # Persist resource.  This is comparable to:
        #    yield self.rc.put_instance(resource)
        self.clients.resource_registry.update(resource)

        # Just return.  This takes the place of the following:
        #    response = yield self.mc.create_instance(MessageContentTypeID = RESOURCE_RESPONSE_TYPE)
        #    response.resource_reference = self.rc.reference_instance(resource)
        #    response.MessageResponseCode = response.ResponseCodes.OK
        #    yield self.reply_ok(msg, response)

    def set_instrument_resource_life_cycle(self, resource_id='', life_cycle_operation={}):
        """
        Set InstrumentResource object lifecycle state by:
        1) call resource registry to read object
        2) set lifecycle_state field
        3) call resource registery to persist updated object
        """

        # Read object.  This is comparable to:
        #    resource = yield self.rc.get_instance(request.resource_reference)
        resource = self.clients.resource_registry.read(resource_id)

        global ACTIVATE
        global DEACTIVATE
        global COMMISSION
        global DECOMMISSION
        global RETIRE
        global DEVELOP

        global ACTIVE
        global INACTIVE
        global COMMISSIONED
        global DECOMMISSIONED
        global RETIRED
        global DEVELOPED

        # Set lifecycle_state field.  This is comparable to:
        if life_cycle_operation == ACTIVATE:
            resource.lifecycle_state = ACTIVE
        elif life_cycle_operation == DEACTIVATE:
            resource.lifecycle_state = INACTIVE
        elif life_cycle_operation == COMMISSION:
            resource.lifecycle_state = COMMISSIONED
        elif life_cycle_operation == DECOMMISSION:
            resource.lifecycle_state = DECOMMISSIONED
        elif life_cycle_operation == RETIRE:
            resource.lifecycle_state = RETIRED
        elif life_cycle_operation == DEVELOP:
            resource.lifecycle_state = DEVELOPED

        # Persist resource.  This is comparable to:
        #    yield self.rc.put_instance(resource)
        self.clients.resource_registry.update(resource)

        # Just return.  This takes the place of the following:
        #    response = yield self.mc.create_instance(MessageContentTypeID = RESOURCE_RESPONSE_TYPE)
        #    response.resource_reference = self.rc.reference_instance(resource)
        #    response.MessageResponseCode = response.ResponseCodes.OK
        #    yield self.reply_ok(msg, response)

def start_client():
    """
    This method will start a container.  We then establish
    an RPC client endpoint to the Bank service and send
    a series of requests.
    """
    container = Container()
    ready = container.start()
    ready.get()
    print 'Client container started'

    client = RPCClient(node=container.node, name="hello_resource", iface=IHelloResourceService)
    print 'RPC endpoint created'

    instrument_info_dict = {}
    instrument_info_dict["name"] = "FooInstrument"
    instrument_info_dict["make"] = "Foo Co."
    instrument_info_dict["model"] = "Foo 2000"
    instrument_info_dict["serial_number"] = "123-456"

    instrument_info = IonObject("InstrumentInfoObject", instrument_info_dict)

    resource_id = client.create_instrument_resource(instrument_info)

    instrument_info.make = "Foo Bar Co."
    instrument_info.model = "Foo Bar 2000"

    client.update_instrument_resource(resource_id, instrument_info)

    global DEVELOP
    client.set_instrument_resource_life_cycle(resource_id, DEVELOP)

    container.stop()