from pyon.core.interceptor.interceptor import Interceptor
from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest
from pyon.core.object import IonObjectBase, walk
from pyon.core.registry import is_ion_object
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

        if self.enabled:
            payload = invocation.message
            log.debug("Payload, pre-validate: %s", payload)

            def validate_ionobj(obj):
                if isinstance(obj, IonObjectBase):
                    invocation.headers["validate"] = True
                return obj

            walk(payload, validate_ionobj)
        return invocation

    def incoming(self, invocation):
        log.debug("ValidateInterceptor.incoming: %s", invocation)

        if self.enabled:
            payload = invocation.message

            # If payload is IonObject, convert from dict to object for processing
            if "format" in invocation.headers and isinstance(payload, dict):
                clzz = invocation.headers["format"]
                if is_ion_object(clzz):
                    payload = IonObject(clzz, payload)

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
                import traceback
                import sys
                (exc_type, exc_value, exc_traceback) = sys.exc_info()
                tb_list = traceback.extract_tb(sys.exc_info()[2])
                tb_list = traceback.format_list(tb_list)
                tb_output = ""
                for elt in tb_list:
                    tb_output += elt
                log.debug("Object validation failed. %s" % e.message)
                log.debug("Traceback: %s" % str(tb_output))
                raise BadRequest(e.message)

        return invocation
