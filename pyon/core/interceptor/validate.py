from pyon.core.interceptor.interceptor import Interceptor, walk
from pyon.core.exception import BadRequest
from pyon.core.object import IonObjectBase
from pyon.util.log import log

class ValidateInterceptor(Interceptor):
    """
    Validates IonObject content within message
    """
    enabled = True

    def configure(self, config):
        if "enabled" in config:
            self.enabled = config["enabled"]
        log.debug("ValidateInterceptor enabled: %s" % str(self.enabled))

    def outgoing(self, invocation):
        # Set validate flag in header if IonObject(s) found in message
        log.debug("ValidateInterceptor.outgoing: %s", invocation)

        if self.enabled == True:
            payload = invocation.message['payload']
            log.debug("Payload, pre-validate: %s", payload)

            def validate_ionobj(obj):
                if isinstance(obj, IonObjectBase):
                    invocation.message["header"]["validate"] = True
                return obj

            walk(payload, validate_ionobj)
        return invocation

    def incoming(self, invocation):
        log.debug("ValidateInterceptor.incoming: %s", invocation)

        if self.enabled == True:
            payload = invocation.message['payload']
            log.debug("Payload, pre-validate: %s", payload)

            # IonObject _validate will throw AttributeError on validation failure.
            # Raise corresponding BadRequest exception into message stack.
            def validate_ionobj(obj):
                if isinstance(obj, IonObjectBase):
                    obj._validate()
                return obj

            try:
                walk(payload, validate_ionobj)
            except AttributeError as e:
                raise BadRequest(e.message)

        return invocation

