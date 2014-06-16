#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'

from M2Crypto import X509

from collections import OrderedDict, defaultdict

# TODO temp imports
from pyon.container import cc
from pyon.core.exception import NotFound
from pyon.net.endpoint import RPCClient
from pyon.util.log import log

#from interface.services.iapp_integration_service import IAppIntegrationService, BaseAppIntegrationService

class AppIntegrationService(object): #(BaseAppIntegrationService):

    def __init__(self, config_params={}):
        log.debug("In __init__")
        pass

    def find_data_resources(self, user_ooi_Id = "", minLatitude = -1.1, maxLatitude = -1.1,
                          minLongitude = -1.1, maxLongitude = -1.1, minVertical = -1.1, maxVertical = -1.1,
                          posVertical = "", minTime = "", maxTime = "", identity = ""):
        return {"dataResourceSummary": [{"datasetMetadata": {"user_ooi_id": "", "data_resource_id": "", "title": "", "institution": ""}, "date_registered": 18446744073709551615, "notificationSet": true}]}


    def register_user(self, certificate = "", rsa_private_key = ""):
        '''
        This op is overloaded.  If the user has never been seen before,
        we attempt to create an OOI user and assign the subject from
        the certificate to the OOI user profile.  The user is then
        "logged in".
        If the user has been seen before, we just "log in" the user.
        '''

        # If default or not all parameters are provided, short circuit and
        # return anonymous user id
        if certificate == "" or rsa_private_key == "":
            return {"ooi_id": "ANONYMOUS", "user_is_admin": false, "user_already_registered": true, "user_is_early_adopter": false, "user_is_data_provider": false, "user_is_marine_operator": false}
        # Else, delegate to Identity Registry
        else:
            # Extract subject from certificate
            # Force conversion to str since it comes across the wire as unicode
            x509 = X509.load_cert_string(str(certificate), format=1)

            subject = str(x509.get_subject())
            is_existing_user = False
            try:
               userinfo = self.clients.identity_registry.find_user_by_subject(subject)
               log.debug("User found")
               is_existing_user = True
            # TODO figure out right exception to catch
            except NotFound as ex:
                # TODO for now just going to use CN portion of subject
                # as new user name
                subj_name = subject.split("/CN=")[-1]
                try:
                    userinfo = self.clients.identity_registry.create_user(subj_name)
                    log.debug("User create succeeded")
                except Exception as ex:
                    # TODO throw exception
                    log.error("Create failed")

            ret = {"ooi_id": userinfo._id}
            ret["user_already_registered"] = is_existing_user
            ret["user_is_admin"] = userinfo.roles.find("ADMIN") != -1
            ret["user_is_early_adopter"] = userinfo.roles.find("EARLY_ADOPTER") != -1
            ret["user_is_data_provider"] = userinfo.roles.find("DATA_PROVIDER") != -1
            ret["user_is_marine_operator"] = userinfo.roles.find("MARINE_OPERATOR") != -1

            return ret

    def get_user(self, user_ooi_id=''):
        try:
            user_info = self.clients.identity_registry.find_user_by_id(user_ooi_id)
            log.debug("User found")
            return user_info
        except:
            # TODO throw not found exception
            log.error("Find failed")

    def update_user_profile(self, user_ooi_id='', name='', institution='', email_address='', profile=[OrderedDict([('name', ''), ('value', '')])]):
        try:
            user_info = self.clients.identity_registry.update_user(name = name, email = email_address, variables = profile)
            log.debug("User updated")
            return user_info
        except:
            # TODO throw not found exception
            log.error("Find failed")

def run_test():
    x509_cert = {'certificate':
 """-----BEGIN CERTIFICATE-----
MIIEMzCCAxugAwIBAgICBQAwDQYJKoZIhvcNAQEFBQAwajETMBEGCgmSJomT8ixkARkWA29yZzEX
MBUGCgmSJomT8ixkARkWB2NpbG9nb24xCzAJBgNVBAYTAlVTMRAwDgYDVQQKEwdDSUxvZ29uMRsw
GQYDVQQDExJDSUxvZ29uIEJhc2ljIENBIDEwHhcNMTAxMTE4MjIyNTA2WhcNMTAxMTE5MTAzMDA2
WjBvMRMwEQYKCZImiZPyLGQBGRMDb3JnMRcwFQYKCZImiZPyLGQBGRMHY2lsb2dvbjELMAkGA1UE
BhMCVVMxFzAVBgNVBAoTDlByb3RlY3ROZXR3b3JrMRkwFwYDVQQDExBSb2dlciBVbndpbiBBMjU0
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA6QhsWxhUXbIxg+1ZyEc7d+hIGvchVmtb
g0kKLmivgoVsA4U7swNDRH6svW242THta0oTf6crkRx7kOKg6jma2lcAC1sjOSddqX7/92ChoUPq
7LWt2T6GVVA10ex5WAeB/o7br/Z4U8/75uCBis+ru7xEDl09PToK20mrkcz9M4HqIv1eSoPkrs3b
2lUtQc6cjuHRDU4NknXaVMXTBHKPM40UxEDHJueFyCiZJFg3lvQuSsAl4JL5Z8pC02T8/bODBuf4
dszsqn2SC8YDw1xrujvW2Bd7Q7BwMQ/gO+dZKM1mLJFpfEsR9WrjMeg6vkD2TMWLMr0/WIkGC8u+
6M6SMQIDAQABo4HdMIHaMAwGA1UdEwEB/wQCMAAwDgYDVR0PAQH/BAQDAgSwMBMGA1UdJQQMMAoG
CCsGAQUFBwMCMBgGA1UdIAQRMA8wDQYLKwYBBAGCkTYBAgEwagYDVR0fBGMwYTAuoCygKoYoaHR0
cDovL2NybC5jaWxvZ29uLm9yZy9jaWxvZ29uLWJhc2ljLmNybDAvoC2gK4YpaHR0cDovL2NybC5k
b2Vncmlkcy5vcmcvY2lsb2dvbi1iYXNpYy5jcmwwHwYDVR0RBBgwFoEUaXRzYWdyZWVuMUB5YWhv
by5jb20wDQYJKoZIhvcNAQEFBQADggEBAEYHQPMY9Grs19MHxUzMwXp1GzCKhGpgyVKJKW86PJlr
HGruoWvx+DLNX75Oj5FC4t8bOUQVQusZGeGSEGegzzfIeOI/jWP1UtIjzvTFDq3tQMNvsgROSCx5
CkpK4nS0kbwLux+zI7BWON97UpMIzEeE05pd7SmNAETuWRsHMP+x6i7hoUp/uad4DwbzNUGIotdK
f8b270icOVgkOKRdLP/Q4r/x8skKSCRz1ZsRdR+7+B/EgksAJj7Ut3yiWoUekEMxCaTdAHPTMD/g
Mh9xL90hfMJyoGemjJswG5g3fAdTP/Lv0I6/nWeH/cLjwwpQgIEjEAVXl7KHuzX5vPD/wqQ=
-----END CERTIFICATE-----""",


    'rsa_private_key':
 """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA6QhsWxhUXbIxg+1ZyEc7d+hIGvchVmtbg0kKLmivgoVsA4U7swNDRH6svW24
2THta0oTf6crkRx7kOKg6jma2lcAC1sjOSddqX7/92ChoUPq7LWt2T6GVVA10ex5WAeB/o7br/Z4
U8/75uCBis+ru7xEDl09PToK20mrkcz9M4HqIv1eSoPkrs3b2lUtQc6cjuHRDU4NknXaVMXTBHKP
M40UxEDHJueFyCiZJFg3lvQuSsAl4JL5Z8pC02T8/bODBuf4dszsqn2SC8YDw1xrujvW2Bd7Q7Bw
MQ/gO+dZKM1mLJFpfEsR9WrjMeg6vkD2TMWLMr0/WIkGC8u+6M6SMQIDAQABAoIBAAc/Ic97ZDQ9
tFh76wzVWj4SVRuxj7HWSNQ+Uzi6PKr8Zy182Sxp74+TuN9zKAppCQ8LEKwpkKtEjXsl8QcXn38m
sXOo8+F1He6FaoRQ1vXi3M1boPpefWLtyZ6rkeJw6VP3MVG5gmho0VaOqLieWKLP6fXgZGUhBvFm
yxUPoNgXJPLjJ9pNGy4IBuQDudqfJeqnbIe0GOXdB1oLCjAgZlTR4lFA92OrkMEldyVp72iYbffN
4GqoCEiHi8lX9m2kvwiQKRnfH1dLnnPBrrwatu7TxOs02HpJ99wfzKRy4B1SKcB0Gs22761r+N/M
oO966VxlkKYTN+soN5ID9mQmXJkCgYEA/h2bqH9mNzHhzS21x8mC6n+MTyYYKVlEW4VSJ3TyMKlR
gAjhxY/LUNeVpfxm2fY8tvQecWaW3mYQLfnvM7f1FeNJwEwIkS/yaeNmcRC6HK/hHeE87+fNVW/U
ftU4FW5Krg3QIYxcTL2vL3JU4Auu3E/XVcx0iqYMGZMEEDOcQPcCgYEA6sLLIeOdngUvxdA4KKEe
qInDpa/coWbtAlGJv8NueYTuD3BYJG5KoWFY4TVfjQsBgdxNxHzxb5l9PrFLm9mRn3iiR/2EpQke
qJzs87K0A/sxTVES29w1PKinkBkdu8pNk10TxtRUl/Ox3fuuZPvyt9hi5c5O/MCKJbjmyJHuJBcC
gYBiAJM2oaOPJ9q4oadYnLuzqms3Xy60S6wUS8+KTgzVfYdkBIjmA3XbALnDIRudddymhnFzNKh8
rwoQYTLCVHDd9yFLW0d2jvJDqiKo+lV8mMwOFP7GWzSSfaWLILoXcci1ZbheJ9607faxKrvXCEpw
xw36FfbgPfeuqUdI5E6fswKBgFIxCu99gnSNulEWemL3LgWx3fbHYIZ9w6MZKxIheS9AdByhp6px
lt1zeKu4hRCbdtaha/TMDbeV1Hy7lA4nmU1s7dwojWU+kSZVcrxLp6zxKCy6otCpA1aOccQIlxll
Vc2vO7pUIp3kqzRd5ovijfMB5nYwygTB4FwepWY5eVfXAoGBAIqrLKhRzdpGL0Vp2jwtJJiMShKm
WJ1c7fBskgAVk8jJzbEgMxuVeurioYqj0Cn7hFQoLc+npdU5byRti+4xjZBXSmmjo4Y7ttXGvBrf
c2bPOQRAYZyD2o+/MHBDsz7RWZJoZiI+SJJuE4wphGUsEbI2Ger1QW9135jKp6BsY2qZ
-----END RSA PRIVATE KEY-----"""}

    container = cc.Container()
    container.start() # :(

    client = RPCClient(node=container.node, name="app_integration", iface=IAppIntegrationService)

    print "Before start client"
    container.start_client('app_integration', client)

    print "Before register user"
    res = client.register_user(x509_cert["certificate"],x509_cert["rsa_private_key"])
    print "After register user: " + str(res)

    container.stop()

if __name__ == '__main__':

    run_test()
