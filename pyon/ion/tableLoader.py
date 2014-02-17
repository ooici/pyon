#!/usr/bin/python
"""
A Service to load data products in to postgres and geoserver
"""

__author__ = 'abird'

import os
from pyon.util.breakpoint import breakpoint
from pyon.public import RT, OT, PRED, LCS, CFG
from ion.services.dm.inventory.dataset_management_service import DatasetManagementService
from interface.services.dm.idataset_management_service import DatasetManagementServiceClient
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


    def reset(self,container):
        #remove all FDT from the DB
        self.cur.execute(self.dropAllFDT())    
        self.con.commit()
        listRows = self.cur.fetchall()
        for row in listRows:
            self.dropExistingTable(row[0],use_cascade =True)    


        #reset the layer information on geoserver
        r = requests.get('http://localhost:8844/service=resetstore&name='+"ooi"+'&id='+"ooi")
        if (DEBUG):
            print r.status_code
            print "SUCCESS!"  


    def populate(self,container):
        pass
            

    #should only be run on start up
    def parse(self, container):
        print "parse Resource Registry.."
        data_products, _ = container.resource_registry.find_resources(restype='DataProduct')
        dsm = DatasetManagementServiceClient()
        #loop through data products
        dpList =[]
        resetGSStore = False
        for dp in data_products:
            data_product_id = dp._id
            dataset_ids, _ = container.resource_registry.find_objects(data_product_id, PRED.hasDataset, id_only=True)
            dataset_id = dataset_ids[0]
            coverage_path = DatasetManagementService._get_coverage_path(dataset_id)

            #dataproduct id and stream information
            stream_def_ids, _ = container.resource_registry.find_objects(data_product_id, PRED.hasStreamDefinition,id_only=True)
            pdict_ids = []

            # StreamDefinition -> ParameterDictionary
            for stream_def_id in stream_def_ids:
                pd_ids, _ = container.resource_registry.find_objects(stream_def_id, PRED.hasParameterDictionary,id_only=True)
                pdict_ids.extend(pd_ids)

            pd_ids = []
            # ParameterDictionary -> ParameterContext
            for pdict_id in pdict_ids:
                pdef_ids, _ = container.resource_registry.find_objects(pdict_id, PRED.hasParameterContext, id_only=False)
                pd_ids.extend(pdef_ids)

            #generate table from params and id
            success = self.generateSQLTable(data_product_id,pd_ids,coverage_path)
            if (success):
                #generate geoserver layer
                r = requests.get('http://localhost:8844/service=addlayer&name='+data_product_id+'&id='+data_product_id)
                if (DEBUG):
                    print r.status_code
                    print "SUCCESS!"
                    dpList.append(pd_ids)
                    print len(dpList)
                                 
        if (DEBUG):
            return dpList

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
                #get the information
                desc =  param['parameter_context']['description']
                ooi_short_name =  param['parameter_context']['ooi_short_name']
                name =  param['parameter_context']['name']
                disp_name = param['parameter_context']['display_name']
                internal_name = param['parameter_context']['internal_name']
                cm_type = param['parameter_context']['param_type']['cm_type']

                units = param.units
                if (not units):
                    try:
                        units= param['parameter_context']['uom']
                        pass
                    except Exception, e:
                        pass
                        #raise e

                value_encoding = param.value_encoding
                if (not value_encoding):
                    value_encoding = param['parameter_context']['param_type']['_value_encoding']

                fill_value = param.fill_value
                std_name = param.standard_name

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
            print coverage_path
            createTableString = self.addServerInfo(createTableString,coverage_path)
            
            if (DEBUG):
                print "\n"
                print createTableString

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
                print "table is already there dropping it"
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
