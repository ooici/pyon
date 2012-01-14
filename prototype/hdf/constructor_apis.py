#!/usr/bin/env python


'''
@package prototype.hdf.constructor_apis
@file prototype/hdf/constructor_apis.py
@author David Stuebe
@brief These constructor classes are only used when building the internal science object model from an external form.
 These are helper classes that contain implicit knowledge of what the user intends to do so that it is not repeated or
 implemented adhoc by the user.
'''



class StationDatasetDefinition(object):
    """
    A science object constructor for a station dataset.
    """

    def __init__(self,):
        """
        Instantiate a station dataset constructor. Create a new one or load an existing datastructure.
        """

    @classmethod
    def LoadStationDefinition(cls, StationDefMetadata):
        pass


    def define_variable(self, name, units, standard_name, dimensions):
        """
        @brief define a variable (quantity) present in the station dataset
        @retval variable id
        """
        pass

    def add_annotation(self, subject_id, name, ):
        pass

    def to_string(self, id):
        """
        return a string containing the metadata for the particular object id for debug purposes.
        """
        pass

    def __str__(self):
        """
        Print the dataset metadata for debug purposes.
        """
        pass

    def _encode_structure(self):
        """
        Method used to encode the station dataset metadata (structure)
        """
        pass


class StationSupplement(object):

    def __init__(self, station_definition=None):
        pass


    def add_station(self, time=None, location=None):
        """
        Add a station to the dataset
        @retval station id
        """

    def add_station_variable(self, station_id, variable=None, values=None, slice=None):
        """
        Add data for a particular variable to a station. Slice represents the map to a know index structure for
        n-dimensional data.
        """

    def add_annotation(self, subject_id=None, annotation=None):
        """
        Add metadata to an object in the dataset
        @retval annotation_id
        """

    def _encode_supplement(self):
        """
        Method used to encode the station dataset supplement
        """


class StationTimeSeries(object):
    """
    A science object constructor for time series dataset at a station.
    """

class Trajectory(object):
    """
    A science object constructor for trajectory data.
    """

class Grid(object):
    """
    A science object constructor for grid data.
    """
