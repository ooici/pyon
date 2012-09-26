""" abstract and default implementation of of a Representation object
    that maps IonObjects to or from a DB-specific data structure
"""

from pyon.core.object import IonObjectSerializer, IonObjectDeserializer
from pyon.core.bootstrap import get_obj_registry


class Representation(object):
    def encode(self, obj, **kw):
        pass

    def decode(self, obj):
        pass


class IonSerializerDictionaryRepresentation(Representation):
    def __init__(self, id_factory):
        self.encoder = IonObjectSerializer()
        self.decoder = IonObjectDeserializer(obj_registry=get_obj_registry())
        self.id_factory = id_factory

    def encode(self, obj, add_id=False):
        out = self.encoder.serialize(obj)
        if add_id and '_id' not in out.keys():
            out['_id'] = self.id_factory.create_id()
        return out

    def decode(self, data):
        return self.decoder.deserialize(data)
