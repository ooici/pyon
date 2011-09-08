#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from zope.interface import implements

from anode.core.bootstrap import CFG
from anode.service.service import BaseService
from interface.services.iapp_integration_service import IAppIntegrationService

class AppIntegrationService(BaseService):
    implements(IAppIntegrationService)

    def findDataResources(self, user_ooi_Id = "", minLatitude = -1.1, maxLatitude = -1.1,
                          minLongitude = -1.1, maxLongitude = -1.1, minVertical = -1.1, maxVertical = -1.1,
                          posVertical = "", minTime = "", maxTime = "", identity = ""):
        return {"dataResourceSummary": [{"datasetMetadata": {"user_ooi_id": "", "data_resource_id": "", "title": "", "institution": ""}, "date_registered": 18446744073709551615, "notificationSet": true}]}


    def registerUser(self, certificate = "", rsa_private_key = ""):
        # If default or not all parameters are provided,
        # return anonymous user id
        if certificate == "" or rsa_private_key == "":
            return {"ooi_id": "ANONYMOUS", "user_is_admin": false, "user_already_registered": true, "user_is_early_adopter": false, "user_is_data_provider": false, "user_is_marine_operator": false}
        # Else, delegate to Identity Registry
        

  