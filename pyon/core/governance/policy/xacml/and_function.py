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
from ndg.xacml.utils import TypedList as Bag


class And(AbstractFunction):
    """Base class for XACML <type>-and functions
@cvar FUNCTION_NS: namespace for this function
@type FUNCTION_NS: string
@cvar BAG_TYPE: type for
@type BAG_TYPE:
"""
    FUNCTION_NS = AbstractFunction.V1_0_FUNCTION_NS + 'and'
    BAG_TYPE = bool

    def evaluate(self, bag):
        """perform AND function on the elements in the bag ref.

access_control-xacml-2.0-core-spec-os, Fe 2005 - A.3.5 Logical functions

@param bag: bag containing elements to be AND'ed
@type bag: ndg.xacml.utils.TypedList

@return: result of AND operation on the inputs
@rtype: bool

"""
        if not isinstance(bag, Bag):
            raise XacmlContextTypeError('Expecting %r derived type for "bag"; '
                                        'got %r' % (Bag, type(bag)))

        if bag.elementType != self.__class__.BAG_TYPE:
            raise XacmlContextTypeError('Expecting %r type elements for "bag"; '
                                        'got %r' %
                                        (self.__class__.BAG_TYPE,
                                         bag.elementType))

        nBagElems = len(bag)
        if nBagElems == 0:
            return True
        else:
            for elem in bag:
                if not elem:
                    return False

        return True

    def evaluate(self, *args):
        """perform AND function on the variable length argument list of elements

access_control-xacml-2.0-core-spec-os, Fe 2005 - A.3.5 Logical functions
access_control-xacml-2.0-core-spec-os, Fe 2005 - 4.2.4.2 ( Rule 2 a[346] ... a[361] )
@param *args: variable number of elements to be AND'ed
@type bool: ndg.xacml.utils.TypedList

@return: result of AND operation on the inputs
@rtype: bool

note: xacml specification cited does not inform whether the and function must expect a bag
hence an alternate implementation for evaluating variable length arguments list.
However, we can infer from the example ( Rule 2 in section 4.2.4.2 )
that the and function can expect a variable length argument list of elements.
"""
        if len(args)==0:
            return True
        else:
            for arg in args:
                if not arg:
                    return False
        return True


class FunctionClassFactory(FunctionClassFactoryInterface):
    """Class Factory for and XACML function class
@cvar FUNCTION_NS: URN for and function
@type FUNCTION_NS: string
"""
    FUNCTION_NS = 'urn:oasis:names:tc:xacml:1.0:function:and'

    def __call__(self, identifier):
        '''Create class for the And XACML function identifier
@param identifier: XACML and function identifier
@type identifier: basestring
@return: and function class or None if identifier doesn't match
@rtype: ndg.xacml.core.functions.v1.and.And / NoneType
'''
        if identifier == And.FUNCTION_NS:
            return And
        else:
            return None