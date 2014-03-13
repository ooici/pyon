#!/usr/bin/env python

"""Messaging interceptor to validate IonObjects"""

from pyon.core.interceptor.interceptor import Interceptor
from pyon.core.bootstrap import IonObject, CFG
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
        self.enabled = self.enabled and CFG.get_safe("container.objects.validate.interceptor", True)
        log.debug("ValidateInterceptor enabled: %s" % str(self.enabled))

    def outgoing(self, invocation):
        # Set validate flag in header if IonObject(s) found in message

        #Nothing to validate on the outbound side
        return invocation

    def incoming(self, invocation):

        if self.enabled:
            payload = invocation.message

            # If payload is IonObject, convert from dict to object for processing
            if "format" in invocation.headers and isinstance(payload, dict):
                clzz = invocation.headers["format"]
                if is_ion_object(clzz):
                    payload = IonObject(clzz, payload)

            #log.debug("Payload, pre-validate: %s", payload)

            # IonObject _validate will throw AttributeError on validation failure.
            # Raise corresponding BadRequest exception into message stack.
            # Ideally the validator should pass on problems, but for now just log
            # any errors and keep going, since logging and seeing invalid situations are better
            # than skipping validation altogether.

            def validate_ionobj(obj):
                if isinstance(obj, IonObjectBase):
                    obj._validate()
                return obj

            try:
                walk(payload, validate_ionobj)
            except AttributeError as e:
                if invocation.headers.has_key("raise-exception") and invocation.headers['raise-exception']:
                    log.warn('message failed validation: %s\nheaders %s\npayload %s', e.message, invocation.headers, payload)
                    raise BadRequest(e.message)
                else:
                    log.warn('message failed validation, but allowing it anyway: %s\nheaders %s\npayload %s', e.message, invocation.headers, payload)
        return invocation
