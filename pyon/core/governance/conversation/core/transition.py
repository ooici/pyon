from abc import ABCMeta, abstractmethod 

class Transition(object):
    __metaclass__= ABCMeta
    @abstractmethod
    def get_trigger(self):
        pass


class DefaultTransition(Transition):     
    def __init__(self, lt_type, label, role):
        self.role = role
        self.label = label
        self.lt_type = lt_type
    def get_trigger(self):
        return "%s_%s_%s" %(self.lt_type, self.label, str.lower(str(self.role)))

    @classmethod
    def create_from_string(cls, from_string):
        [type, label, role] = from_string.split('_')
        return cls(type, label, role)

class AssertionTransition(Transition):
    __metaclass__= ABCMeta
    @abstractmethod
    def get_payload_variable(self):
        pass
    @abstractmethod
    def get_assertion(self):
        pass
        
class PayloadTransition(Transition):
    @abstractmethod
    def get_peyload(self):
        pass
    
    
class DefaultAssertionTransition(AssertionTransition):
    def __init__(self, lt_type, label, role, payload, assertion):
        self.role = role
        self.label = label
        self.lt_type = lt_type
        self.payload = payload
        self.assertion = assertion
        
    def get_trigger(self):
        return "%s_%s_%s" %(self.lt_type, self.label, self.str.lower(str(self.role)))
    def get_payload_variable(self):
        return self.payload
    def get_assertion(self):
        return self.asserti    
    
class TransitionFactory:
    @classmethod
    def create(cls, lt_type, label, role, settings = None):
        if (settings == None):
            return "%s_%s_%s" %(lt_type, label, str.lower(str(role)))
