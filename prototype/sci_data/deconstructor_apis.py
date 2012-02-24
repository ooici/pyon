'''
@package prototype.hdf.deconstructor_apis
@file prototype/hdf/deconstructor_apis.py
@author Tim Giguere
@brief This deconstructor class is only used when re-building the internal science object model from an external form.
 These are helper classes that contain implicit knowledge of what the user intends to do so that it is not repeated or
 implemented adhoc by the user.
'''

from interface.objects import CoordinateAxis
from interface.objects import StreamDefinitionContainer
from prototype.hdf.hdf_codec import HDFDecoder, HDFDecoderException

from pyon.util.log import log

class PointSupplementDeconstructor(object):

    def __init__(self, stream_definition=None, stream_granule_container=None):
        """
        @param stream_granule_container is the incoming packet object defining the point record for this stream
        """

        self._stream_definition = stream_definition

        data_stream_id = stream_granule_container.data_stream_id
        data_stream = stream_granule_container.identifiables[data_stream_id]

        self._hdf_string = data_stream.values

    def get_values(self, name=''):
        return self._decode_supplement(self._hdf_string, name)

    def _decode_supplement(self, hdf_string='', name=''):
        """
        Method used to encode the point dataset supplement
        """

        if hdf_string == '':
            return

        # build the hdf and return the ion-object...
        try:
            import numpy
            decoder = HDFDecoder(hdf_string)

            return decoder.read_hdf_dataset(name)

        except :
            log.exception('HDF decoder failed. Please make sure you have it properly installed!')