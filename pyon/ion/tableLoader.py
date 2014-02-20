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
REMOVELAYER = "removelayer"
ADDLAYER = "addlayer"

SERVER = "http://localhost:8844"

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


    def sendGeoNodeRequest(self,request,resource_id, prim_types=None):
        try:
            
            if prim_types is None:
                r = requests.get(SERVER+'/service='+request+'&name='+resource_id+'&id='+resource_id)
                self.processStatusCode(r.status_code) 
            else:
                r = requests.get(SERVER+'/service='+request+'&name='+resource_id+'&id='+resource_id+"&params="+str(prim_types))
                self.processStatusCode(r.status_code) 
                
        except Exception, e:
            raise e

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
        self.sendGeoNodeRequest(REMOVELAYER,resource_id)

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
        [success,prim_types]= self.generateSQLTable(new_resource_id,param_dict,relevant,coverage_path)

        print prim_types

        if (success):
            #generate geoserver layer
            self.sendGeoNodeRequest(ADDLAYER,new_resource_id,prim_types)
    
    def getValueEncoding(self,name,value_encoding):
        encodingString = None
        prim_type = None
        #get the primitve type, and generate something using NAME
        if name =="time":
            encodingString="\""+name+"\" "+TIMEDATE
            prim_type = "time"
        elif (name.find('time')>=0):
            #ignore other times
            encodingString=None
            prim_type = None
        elif (value_encoding.startswith('int')):
            #int                                
            encodingString="\""+name+"\" "+INT
            prim_type = "int"
        elif(value_encoding.find('i8')>-1):    
            #int
            encodingString="\""+name+"\" "+INT
            prim_type = "int"
        elif(value_encoding.startswith('float')):
            #float
            encodingString="\""+name+"\" "+REAL
            prim_type = "real"
        elif(value_encoding.find('f4')>-1):
            #float
            encodingString="\""+name+"\" "+REAL    
            prim_type = "real"
        elif(value_encoding.find('f8')>-1):
            #float
            encodingString="\""+name+"\" "+REAL    
            prim_type = "real"
        else:
            encodingString=None
            prim_type = None
             #no value encoding available   
        return (encodingString, prim_type)

    """
    Generates Foreign data table for used with postgres
    """
    def generateSQLTable(self, dataset_id, params, relevant,coverage_path):
        #check table exists
        if (not self.doesTableExist(dataset_id)):

            valid_types={}
            createTableString ="create foreign table \""+dataset_id+"\" ("

            #loop through the params
            for param in relevant:
                #get the information
                dataItem = params[param]
                desc =  dataItem[1]['description']
                ooi_short_name =  dataItem[1]['ooi_short_name']
                name =  dataItem[1]['name']
                disp_name = dataItem[1]['display_name']
                internal_name = dataItem[1]['internal_name']
                cm_type = dataItem[1]['param_type']['cm_type']
                units = ""
                try:
                    units= dataItem[1]['uom']
                except Exception, e:
                    print "no units available..."
                
                value_encoding = dataItem[1]['param_type']['_value_encoding']
                fill_value = dataItem[1]['param_type']['_fill_value']
                std_name = dataItem[1]['standard_name']

                #only use things that have valid value
                if (len(name)>0): #and (len(desc)>0) and (len(units)>0) and (value_encoding is not None)):
                    if (DEBUG):
                        print "-------processed-------"
                        print ooi_short_name
                        print desc
                        print name
                        print disp_name
                        print units
                        print internal_name
                        print value_encoding
                        print cm_type[1]

                    #is it a time field, i.e goes the name contain time
                    #if (name.find('time')>=0):
                    #    createTableString+="\""+name+"\" "+TIMEDATE
                    #else:
                    if (cm_type[1] == "ArrayType"):
                        pass
                    else:
                        [encoding,prim_type] = self.getValueEncoding(name,value_encoding)          
                        if encoding is not None:
                            createTableString+=encoding
                            valid_types[name] = prim_type

                pass

            #createTableString+=LATITUDE+" "+REAL
            #createTableString+=LONGITUDE+" "+REAL

            pos = createTableString.rfind(',')
            createTableString = createTableString[:pos] + ' ' + createTableString[pos+1:]
            print coverage_path
            createTableString = self.addServerInfo(createTableString,coverage_path)
            
            if (DEBUG):
                print "\n"
                print createTableString

            try:
                self.cur.execute(createTableString)
                self.con.commit()

                self.cur.execute(self.generateTableView(dataset_id,"lat","lon"))
                self.con.commit()

                return ((self.doesTableExist(dataset_id)),valid_types)

            except Exception, e:
                #error setting up connection
                print 'Error %s' % e

        else:
            if (DEBUG):
                print "table is already there dropping it"
            self.dropExistingTable(dataset_id)
            return False



    '''
    generate table view including geom
    '''
    def generateTableView(self,dataset_id,lat_field,lon_field):
        sqlquery = '''
        CREATE or replace VIEW "_%s_view" as SELECT ST_SetSRID(ST_MakePoint(%s, %s),4326) as 
        geom, * from "%s";
        '''% (dataset_id,lon_field,lat_field,dataset_id)
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
