'''
@package prototype.hdf.stream_parser
@file prototype/hdf/stream_parser.py
@author Tim Giguere
@author David Stuebe
@brief This stream_parser class is only used when re-building the internal science object model from an external form.
 These are helper classes that contain implicit knowledge of what the user intends to do so that it is not repeated or
 implemented adhoc by the user.
'''

from interface.objects import CoordinateAxis
from interface.objects import StreamDefinitionContainer
from prototype.hdf.hdf_codec import HDFDecoder, HDFDecoderException

from pyon.util.log import log

class PointSupplementStreamParser(object):

    def __init__(self, stream_definition=None, stream_granule=None):
        """
        @param stream_granule_container is the incoming packet object defining the point record for this stream
        """

        self._stream_definition = stream_definition

        self._stream_granule = stream_granule

        data_stream_id = stream_granule.data_stream_id
        data_stream = stream_granule.identifiables[data_stream_id]

        hdf_string = data_stream.values

        self._decoder = HDFDecoder(hdf_string)


    def get_values(self, field_name=''):

        hdf_path = self._get_hdf_path(field_name)

        return self._decoder.read_hdf_dataset(hdf_path)

    def _get_hdf_path(self, field_name):

        identifiables = self._stream_definition.identifiables
        # Let the exception buble if this doesn't work...

        #@todo check to make sure this range id is in the stream granule?

        return identifiables[identifiables[field_name].range_id].values_path

    def list_field_names(self):
        """
        Debug method to list the field names in the stream definition

        Currently does not check to see if the range for the field is in this supplement!
        """

        identifiables = self._stream_definition.identifiables

        data_stream_id = self._stream_definition.data_stream_id

        element_type_id = identifiables[data_stream_id].element_type_id

        data_record_id = identifiables[element_type_id].data_record_id

        return identifiables[data_record_id].field_ids

