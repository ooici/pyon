from abc import ABCMeta, abstractmethod 
class ConversationMessageAdapter(object):
    __metaclass__= ABCMeta
    @abstractmethod
    def to_conversation_msg(self, rawMsg):
        pass
    @abstractmethod
    def to_invitation_msg(self, invitation):
        pass
    @abstractmethod
    def from_invitation_msg(self):
        pass
    @abstractmethod
    def from_converastion_msg(self):
        pass 