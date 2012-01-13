#!/usr/bin/env python


'''
@package prototype.hdf.constructor_apis
@file prototype/hdf/constructor_apis.py
@author David Stuebe
@brief These constructor classes are only used when building the internal science object model from an external form.
 These are helper classes that contain implicit knowledge of what the user intends to do so that it is not repeated or
 implemented adhoc by the user.
'''



class Station(object):
    """
    A science object constructor for a station dataset.
    """

    def __init__(self, datastructure=None):
        """
        Instantiate a station dataset constructor. Create a new one or load an existing datastructure.
        """

    def add_station(self, time=None, location=None):
        """
        Add a station to the dataset
        @retval station id
        """
    def add_station_variable(self, variable=None, values=None, slice=None):
        """
        Add data for a particular variable to a station. Slice represents the map to a know index structure for
        n-dimensional data.
        """

    def add_annotation(self, subject=None, annotation=None):
        """
        Add metadata to an object in the dataset
        @retval annotation_id
        """

    def define_variable(self):
        """
        @brief define a variable (quantity) present at a station
        @retval variable id
        """

    def to_string(self, id):
        """
        return a string containing the metadata for the particular object id for debug purposes.
        """

    def __str__(self):
        """
        Print the dataset metadata for debug purposes.
        """

    def _encode_supplement(self):
        """
        Method used to encode the station dataset supplement
        """

    def _encode_structure(self):
        """
        Method used to encode the station dataset metadata (structure)
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
