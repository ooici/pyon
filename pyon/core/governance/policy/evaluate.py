"""
Contains a class to evaluate python code and return True or False
"""
__author__ = "Stephen Henrie"
__date__ = "04/13/2013"


from ndg.xacml.core.context.exceptions import XacmlContextTypeError
from ndg.xacml.core.functions import (AbstractFunction, FunctionClassFactoryInterface)
from ndg.xacml.core.attributevalue import (AttributeValue,
                                           AttributeValueClassFactory)
from ndg.xacml.utils import TypedList as Bag

from pyon.core.governance.governance_dispatcher import GovernanceDispatcher
from pyon.util.execute import execute_method
from pyon.util.log import log
class EvaluateCode(AbstractFunction):
    """Generic equal function for all types

    @cvar TYPE: attribute type for the given implementation.  Derived classes
    should set appropriately
    @type TYPE: NoneType
    """
    FUNCTION_NS = 'urn:oasis:names:tc:xacml:ooi:function:evaluate-code'
    ATTRIB1_TYPE = basestring
    ATTRIB2_TYPE = dict

    def evaluate(self, *inputs):
        """Match input attribute values

        @param attribute1: a segment of code to evaluate
        @type attribute1: ndg.xacml.core.attributevalue.AttributeValue derived
        @param attribute2: a dict with the message parameters
        @type attribute2: ndg.xacml.core.attributevalue.AttributeValue derived
        @return: True if code evaluates to True, False otherwise
        @rtype: bool
        """
        error_msg = ''
        eval_code = inputs[0]
        if not isinstance(eval_code, AttributeValue) and not isinstance(eval_code.elementType, self.__class__.ATTRIB1_TYPE):
            raise XacmlContextTypeError('Expecting %r derived type for '
                                        '"attribute1"; got %r' %
                                        (self.__class__.ATTRIB1_TYPE,
                                         type(eval_code)))

        if isinstance(inputs[1], Bag):
            parameter_dict = inputs[1][0]
        else:
            parameter_dict = inputs[1]

        if not isinstance(parameter_dict, AttributeValue) and not isinstance(parameter_dict.elementType, self.__class__.ATTRIB2_TYPE):
            raise XacmlContextTypeError('Expecting %r derived type for '
                                        '"attribute2"; got %r' %
                                        (self.__class__.ATTRIB2_TYPE,
                                         type(parameter_dict)))

        try:
            exec eval_code.value
            pref = locals()["policy_func"]
            ret_val, error_msg = pref(process=parameter_dict.value['process'], message=parameter_dict.value['message'], headers=parameter_dict.value['headers'])
            if not ret_val:
                parameter_dict.value['annotations'][GovernanceDispatcher.POLICY__STATUS_REASON_ANNOTATION] = error_msg

        except Exception, e:
            log.exception(e)
            ret_val = False
            parameter_dict.value['annotations'][GovernanceDispatcher.POLICY__STATUS_REASON_ANNOTATION] = e.message

        return ret_val

class EvaluateFunction(AbstractFunction):
    """Generic equal function for all types

    @cvar TYPE: attribute type for the given implementation.  Derived classes
    should set appropriately
    @type TYPE: NoneType
    """
    FUNCTION_NS = 'urn:oasis:names:tc:xacml:ooi:function:evaluate-function'
    ATTRIB1_TYPE = basestring
    ATTRIB2_TYPE = dict

    def evaluate(self, *inputs):
        """Match input attribute values

        @param attribute1: the name of a function to execute
        @type attribute1: ndg.xacml.core.attributevalue.AttributeValue derived
        @param attribute2: an object where the function is located
        @type attribute2: ndg.xacml.core.attributevalue.AttributeValue derived
        @param attribute3: an optional dict with the message parameters
        @type attribute3: ndg.xacml.core.attributevalue.AttributeValue derived
        @return: True if code evaluates to True, False otherwise
        @rtype: bool
        """
        error_msg = ''
        function_name = inputs[0]
        if not isinstance(function_name, AttributeValue) and not isinstance(function_name.elementType, self.__class__.ATTRIB1_TYPE):
            raise XacmlContextTypeError('Expecting %r derived type for '
                                        '"attribute1"; got %r' %
                                        (self.__class__.ATTRIB1_TYPE,
                                         type(function_name)))

        if isinstance(inputs[1], Bag):
            parameter_dict = inputs[1][0]
        else:
            parameter_dict = inputs[1]
        if not isinstance(parameter_dict, AttributeValue) and not isinstance(parameter_dict.elementType, self.__class__.ATTRIB2_TYPE):
            raise XacmlContextTypeError('Expecting %r derived type for '
                                        '"attribute2"; got %r' %
                                        (self.__class__.ATTRIB2_TYPE,
                                         type(parameter_dict)))

        try:
            ret_val, error_msg = execute_method(execution_object=parameter_dict.value['process'], method_name=function_name.value, **parameter_dict.value)
            if not ret_val:
                parameter_dict.value['annotations'][GovernanceDispatcher.POLICY__STATUS_REASON_ANNOTATION] = error_msg
        except Exception, e:
            log.exception(e)
            ret_val = False
            parameter_dict.value['annotations'][GovernanceDispatcher.POLICY__STATUS_REASON_ANNOTATION] = e.message

        return ret_val


class FunctionClassFactory(FunctionClassFactoryInterface):
    """Class Factory for and XACML function class
        @cvar FUNCTION_NS: URN for and function
        @type FUNCTION_NS: string
    """

    def __call__(self, identifier):
        '''Create class for the And XACML function identifier
        @param identifier: XACML and function identifier
        @type identifier: basestring
        @return: and function class or None if identifier doesn't match
        @rtype: ndg.xacml.core.functions.v1.and.And / NoneType
        '''
        if identifier == EvaluateCode.FUNCTION_NS:
            return EvaluateCode
        elif identifier == EvaluateFunction.FUNCTION_NS:
            return EvaluateCode
        else:
            return None

