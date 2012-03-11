
from abc import ABCMeta, abstractmethod
class BaseParser:
    __metaclass__= ABCMeta
    @abstractmethod
    def parse(self, filename):
        pass
