import numpy, h5py

from prototype.hdf.science_object_codec import HDFEncoder, HDFDecoder

array = numpy.ones((4,5))
dataset_name = 'rootgroup/mygroup/data/temperature'

hdfencoder = HDFEncoder()
hdfencoder.add_hdf_dataset(dataset_name, array)
hdfstring = hdfencoder.encoder_close()

hdfdecoder = HDFDecoder(hdfstring)
hdfdecoder.read_hdf_dataset(dataset_name)
