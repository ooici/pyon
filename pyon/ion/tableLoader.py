#!/usr/bin/python
"""
A Service to load data products in to postgres and geoserver
"""

__author__ = 'abird'

import os
from pyon.util.breakpoint import breakpoint
from pyon.ion.resource import LCS, LCE, PRED
from pyon.util.file_sys import FileSystem, FS
#from ion.services.dm.inventory.dataset_management_service import DatasetManagementService
import time
import psycopg2
import sys
import requests

coverageFDWSever = "cov_srv"
DEBUG = True

REAL = "real,"
INT = "int,"
TIMEDATE = "timestamp,"

LATITUDE = "latitude"
LONGITUDE = "longitude"

RESETSTORE = "resetstore"


class resource_parser():

    def __init__(self):
        self.con = None
        try:
            self.con = psycopg2.connect(database='postgres', user='rpsdev')
            self.cur = self.con.cursor()

            self.cur.execute('SELECT version()')
            ver = self.cur.fetchone()
            print ver

        except psycopg2.DatabaseError, e:
            #error setting up connection
            print 'Error %s' % e

    def close(self):
        if self.con:
            self.con.close()


    def sendGeoNodeRequest(self,request,resource_id):
        r = requests.get('http://localhost:8844/service='+request+'&name='+resource_id+'&id='+resource_id)
        self.processStatusCode(r.status_code) 
            

    '''
    Reset all data and rows, and layers
    '''
    def reset(self):
        #remove all FDT from the DB
        self.cur.execute(self.dropAllFDT())    
        self.con.commit()
        listRows = self.cur.fetchall()
        for row in listRows:
            self.dropExistingTable(row[0],use_cascade =True)    

        #reset the layer information on geoserver
        self.sendGeoNodeRequest(RESETSTORE,"ooi") 

    def processStatusCode(self,status_code):        
        if (status_code ==200):
            print "SUCCESS!"
        else:
            print "Error Processing layer"

    @staticmethod
    def _get_coverage_path(dataset_id):
        file_root = FileSystem.get_url(FS.CACHE,'datasets')
        return os.path.join(file_root, '%s' % dataset_id)        

    '''
    removes a single resource
    '''
    def removeSingleResource(self,resource_id):
        if (self.doesTableExist(resource_id)):
            self.dropExistingTable(resource_id,use_cascade =True) 
        else:
            print "could not remove,does not exist"
            pass

        # try and remove it from geoserver
        r = requests.get('http://localhost:8844/service=removelayer&name='+resource_id+'&id='+resource_id)
        self.processStatusCode(r.status_code)      

    '''
    creates a single resource
    '''
    def createSingleResource(self,new_resource_id,param_dict):
        #parse 
        relevant = []
        for k,v in param_dict.iteritems():
            if isinstance(v, list) and len(v)==2 and 'param_type' in v[1]:
                relevant.append(k)
        print 'params are', relevant

        coverage_path = self._get_coverage_path(new_resource_id)

        #generate table from params and id
        success = self.generateSQLTable(new_resource_id,param_dict,coverage_path)

        if (success):
            #generate geoserver layer
            r = requests.get('http://localhost:8844/service=addlayer&name='+new_resource_id+'&id='+new_resource_id)
            self.processStatusCode(r.status_code)

    """
    Generates Foreign data table for used with postgres
    """
    def generateSQLTable(self, dataset_id, params,coverage_path):
        #check table exists
        if (not self.doesTableExist(dataset_id)):

            createTableString ="create foreign table \""+dataset_id+"\" ("

            #loop through the params
            data_params =[]
            for param in params:
                dataItem = params[param]

                if (len(dataItem) >1):
                    #get the information
                    desc =  dataItem[1]['description']
                    ooi_short_name =  dataItem[1]['ooi_short_name']
                    name =  dataItem[1]['name']
                    disp_name = dataItem[1]['display_name']
                    internal_name = dataItem[1]['internal_name']
                    cm_type = dataItem[1]['param_type']['cm_type']
                    units= dataItem[1]['uom']
                    value_encoding = dataItem[1]['param_type']['_value_encoding']
                    fill_value = dataItem[1]['param_type']['_fill_value']
                    std_name = dataItem[1]['standard_name']

                    #only use things that have valid value
                    if (len(name)>0): #and (len(desc)>0) and (len(units)>0) and (value_encoding is not None)):
                        if (DEBUG):
                            print "-------processed-------"
                            print name
                            print units
                            print value_encoding
                            print cm_type[1]

                        #is it a time field, i.e goes the name contain time
                        if (name.find('time')>=0):
                            createTableString+="\""+name+"\" "+TIMEDATE
                        else:
                            if (cm_type[1] == "ArrayType"):
                                pass
                            else:          
                                #get the primitve type, and generate something using NAME
                                if (value_encoding.startswith('int')):
                                    #int                                
                                    createTableString+="\""+name+"\" "+INT

                                elif(value_encoding.find('i8')>-1):    
                                    #int
                                    createTableString+="\""+name+"\" "+INT

                                elif(value_encoding.startswith('float')):
                                    #float
                                    createTableString+="\""+name+"\" "+REAL

                                elif(value_encoding.find('f4')>-1):
                                    #float
                                    createTableString+="\""+name+"\" "+REAL    

                                elif(value_encoding.find('f8')>-1):
                                    #float
                                    createTableString+="\""+name+"\" "+REAL    
                                else:
                                     #no value encoding available
                                    #createTableString+="\""+name+"\" "+REAL  
                                    pass

                    pass

                createTableString+=LATITUDE+" "+REAL
                createTableString+=LONGITUDE+" "+REAL

                pos = createTableString.rfind(',')
                createTableString = createTableString[:pos] + ' ' + createTableString[pos+1:]
               
                createTableString = self.addServerInfo(createTableString,coverage_path)
                
                if (DEBUG):
                    print "\n"
                    print createTableString
                    print "\n"
                    print coverage_path

                try:
                    self.cur.execute(createTableString)
                    self.con.commit()

                    self.cur.execute(self.generateTableView(dataset_id))
                    self.con.commit()

                    return (self.doesTableExist(dataset_id))

                except Exception, e:
                    #error setting up connection
                    print 'Error %s' % e

        else:
            if (DEBUG):
                print "table is already there dropping it..."
            self.dropExistingTable(dataset_id)
            return False


    '''
    generate table view including geom
    '''
    def generateTableView(self,dataset_id):
        sqlquery = '''
        CREATE or replace VIEW "%s_view" as SELECT ST_SetSRID(ST_MakePoint(10, 10),4326) as 
        geom, * from "%s";
        '''% (dataset_id,dataset_id)
        return sqlquery

    '''
    add the server info to the sql create table request
    '''
    def addServerInfo(self, sqlquery,coverage_path):
        sqlquery += ") server " +coverageFDWSever+ " options(k \'1\',cov_path \'"+coverage_path+"\');"
        return sqlquery

    def modifySQLTable(self, dataset_id, params):
        print "sql modify"

    def removeSQLTable(self, dataset_id):
        print "sql remove"

    def dropExistingTable(self, dataset_id,use_cascade =False):
        self.cur.execute(self.getTableDropCmd(dataset_id))
        self.con.commit()

    '''
    Checks to see if the table already exists before we add it
    '''    
    def doesTableExist(self,dataset_id):
        self.cur.execute(self.getTableExistCmd(dataset_id))
        out = self.cur.fetchone()
        #check table exist
        if (out is None):
            return False
        else:
            return True

    '''
    looks in the psql catalog for the table, therefore is quick and does not hit the table itself
    '''
    def getTableExistCmd(self,dataset_id):
        #check table exists 
        sqlcmd = "SELECT 1 FROM pg_catalog.pg_class WHERE relname = \'"+dataset_id+"\';"
        return sqlcmd


    def getTableDropCmd(self,dataset_id,use_cascade =False):
        #drop table
        if (use_cascade):
            sqlcmd = "drop foreign table \""+dataset_id+"\" cascade;"
        else:
            sqlcmd = "drop foreign table \""+dataset_id+"\" cascade;"    
        return sqlcmd

    def dropAllFDT(self):
        sqlcmd = "SELECT relname FROM pg_catalog.pg_class where relkind ='foreign table';"
        return sqlcmd        
