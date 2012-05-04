import hashlib

from pyon.container.cc import Container
from pyon.core.interceptor.interceptor import Interceptor
from pyon.core.security import authentication
from pyon.core.exception import BadRequest
from pyon.util.log import log

class SignatureInterceptor(Interceptor):
    def __init__(self, *args, **kwargs):
        self.auth = authentication.Authentication()

    def outgoing(self, invocation):
        if Container.instance.private_key:
            hash = hashlib.sha1(invocation.message).hexdigest()
            invocation.headers['signature'] = self.auth.sign_message(hash, Container.instance.private_key)
            invocation.headers['signer'] = "ion"
            log.debug("Signing message with ")
        
        return invocation

    def incoming(self, invocation):
        if 'signature' in invocation.headers and 'signer' in invocation.headers:
            hash = hashlib.sha1(invocation.message).hexdigest()
            if not self.auth.verify_message(hash, Container.instance.cert, invocation.headers['signature']):
                raise BadRequest("Digital signature invalid")
        return invocation
