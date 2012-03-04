"""NDG XACML one and only functions module

NERC DataGrid
"""
__author__ = "Prashant Kediyal"
__date__ = "03/01/12"
__copyright__ = ""
__license__ = "BSD - see LICENSE file in top-level directory"
__contact__ = "pkediyal@gmail.com"
__revision__ = '$Id: $'
from ndg.xacml.core.functions import (AbstractFunction,
                                      FunctionClassFactoryInterface)
from ndg.xacml.core.context.exceptions import XacmlContextTypeError


class Not(AbstractFunction):
    """Base class for XACML <type>-and functions
@cvar FUNCTION_NS: namespace for this function
@type FUNCTION_NS: string
@cvar BAG_TYPE: type for
@type BAG_TYPE:
"""
    FUNCTION_NS = AbstractFunction.V1_0_FUNCTION_NS + 'not'
    ATTRIBUTE_TYPE = bool

    def evaluate(self, attribute=None):
        """perform not function on the element

access_control-xacml-2.0-core-spec-os, Fe 2005 - A.3.5 Logical functions

@param attribute: elements to be NOT'ed
@type bool: bool

@return: result of NOT operation on the inputs
@rtype: bool

"""
        if type(attribute) != self.__class__.ATTRIBUTE_TYPE:
            raise XacmlContextTypeError('Expecting %r type for attribute; '
                                        'got %r' %
                                        (self.__class__.ATTRIBUTE_TYPE,
                                         type(attribute)))

        if attribute is None:
            response = False
        else:
            response = not attribute

        return response


class FunctionClassFactory(FunctionClassFactoryInterface):
    """Class Factory for not XACML function class
@cvar FUNCTION_NS: URN for not function
@type FUNCTION_NS: string
"""
    FUNCTION_NS = 'urn:oasis:names:tc:xacml:1.0:function:not'

    def __call__(self, identifier):
        '''Create class for the Not XACML function identifier
@param identifier: XACML and function identifier
@type identifier: basestring
@return: and function class or None if identifier doesn't match
@rtype: ndg.xacml.core.functions.v1.not.Not / NoneType
'''
        if identifier == Not.FUNCTION_NS:
            return Not
        else:
            return None