import numpy, h5py

from prototype.hdf.science_object_codec import HDFEncoder, HDFDecoder

array = numpy.ones((4,5))
dataset_name = 'rootgroup/mygroup/data/temperature'

# Create an encoder object
hdfencoder = HDFEncoder()
# Add data as an array
hdfencoder.add_hdf_dataset(dataset_name, array)
# Convert all the data to a binary string for easy transportation
hdfstring = hdfencoder.encoder_close()

# Create a decoder object
hdfdecoder = HDFDecoder(hdfstring)
# Read the array out of the decoder
hdfdecoder.read_hdf_dataset(dataset_name)
