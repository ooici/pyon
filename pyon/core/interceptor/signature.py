from collections import OrderedDict

from pyon.container.cc import Container
from pyon.core.exception import BadRequest
from pyon.core.interceptor.interceptor import Interceptor
from pyon.core.object import IonObjectSerializationBase
from pyon.core.security import authentication


class DictSorter(IonObjectSerializationBase):
    serialize = IonObjectSerializationBase.operate

    def _transform(self, obj):
        if isinstance(obj, dict):
            res = OrderedDict()
            for key in sorted(obj):
                res[key] = obj[key]
            return res

        return obj


class SignatureInterceptor(Interceptor):
    def __init__(self, *args, **kwargs):
        Interceptor.__init__(self)
        self._dict_sorter = DictSorter()
        self.auth = authentication.Authentication()

    def outgoing(self, invocation):
        msg = str(self._dict_sorter.serialize(invocation.message))
        if self.auth.authentication_enabled():
            signer = 'no-signer'
            if Container.instance is not None:
                signer = Container.instance.id
            invocation.headers['signature'] = self.auth.sign_message(msg)
            invocation.headers['signer'] = signer
            invocation.headers['certificate'] = self.auth.get_container_cert()

        return invocation

    def incoming(self, invocation):
        msg = str(self._dict_sorter.serialize(invocation.message))
        if self.auth.authentication_enabled():
            headers = invocation.headers
            if not 'signature' in headers or not 'signer' in headers or not 'certificate' in headers:
                raise BadRequest("Digital signature missing from request")
            status, cause = self.auth.verify_message(msg, headers['certificate'], headers['signature'])
            if status != 'Valid':
                raise BadRequest("Digital signature invalid. Cause %s" % cause)
        return invocation
