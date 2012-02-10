import numpy, h5py

from prototype.hdf.hdf_codec import HDFEncoder, HDFDecoder

array1 = numpy.ones((4,5))
array2 = numpy.ones((2,3))
array3 = numpy.ones((10,2))
dataset_name1 = 'rootgroup/mygroup/data/temperature'
dataset_name2 = 'rootgroup/mygroup/data/pressure'
dname = 'aGroup/adataset'

###########################################################

# Create an encoder object
hdfencoder = HDFEncoder()
# Add data as an array
hdfencoder.add_hdf_dataset(dataset_name1, array1)
hdfencoder.add_hdf_dataset(dataset_name2, array2)
# Convert all the data to a binary string for easy transportation
hdfstring1 = hdfencoder.encoder_close()

# Create another encoder. This time pass on name of hdf5 file to write
hdfencoder = HDFEncoder('/tmp/testHDFEncoder.hdf5')
hdfencoder.add_hdf_dataset(dataset_name1, array1)
hdfencoder.add_hdf_dataset(dataset_name2, array2)
# Convert all the data to a binary string for easy transportation
hdfstring2 = hdfencoder.encoder_close()

# Create another encoder. This time pass on name of hdf5 file to write
hdfencoder = HDFEncoder('/tmp/testHDFEncoder.hdf5')
hdfencoder.add_hdf_dataset(dname, array3)
# Convert all the data to a binary string for easy transportation
hdfstring3 = hdfencoder.encoder_close()

##########################################################

print('Dataset: %s ' % dataset_name2)
# Create a decoder object
hdfdecoder = HDFDecoder(hdfstring1)
# Read the array out of the decoder
print hdfdecoder.read_hdf_dataset(dataset_name2)

print('Dataset: %s ' % dataset_name1)
# Create a decoder object
hdfdecoder = HDFDecoder(hdfstring2)
# Read the array out of the decoder
print hdfdecoder.read_hdf_dataset(dataset_name1)

#print "Third decoded hdf_string: "
## Create a decoder object
hdfdecoder = HDFDecoder(hdfstring3)
# Read the array out of the decoder
print('Dataset: %s ' % dataset_name1)
print hdfdecoder.read_hdf_dataset(dataset_name1)

hdfdecoder = HDFDecoder(hdfstring3)
print("Dataset: %s" % dataset_name2)
print hdfdecoder.read_hdf_dataset(dataset_name2)

hdfdecoder = HDFDecoder(hdfstring3)
print("Dataset: %s" % dname)
print hdfdecoder.read_hdf_dataset(dname)
