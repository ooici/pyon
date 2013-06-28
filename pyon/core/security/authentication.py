#!/usr/bin/env python

"""
@file ion/core/security/authentication.py
@author Roger Unwin
@author Dorian Raymer
@brief routines for working with crypto (x509 certificates and private_keys)
"""

import binascii
import urllib
import os
import datetime
import hashlib

from M2Crypto import EVP, X509

from pyon.core.bootstrap import CFG
from pyon.container.cc import Container
from pyon.util.log import log

#XXX @note What is this?
#sys.path.insert(0, "build/lib.linux-i686-2.4/")

#XXX @todo Fix: Should not need absolute paths.
BASEPATH = os.path.realpath(".")
CERTSTORE_PATH = BASEPATH + '/res/certstore/'
KEYSTORE_PATH = BASEPATH + '/res/keystore/'

CONTAINER_CERT_NAME = 'container.crt'
CONTAINER_KEY_NAME = 'container.key'
ORG_CERT_NAME = 'root.crt'


class Authentication(object):
    """
    routines for working with crypto (x509 certificates and private_keys)
    """
    def __init__(self):
        self.cont_cert = None
        self.cont_key = None
        self.root_cert = None
        self.white_list = []

        # Look for certificates and keys in "the usual places"
        certstore_path = self.certstore = CFG.get_safe('authentication.certstore', CERTSTORE_PATH)
        log.debug("certstore_path: %s" % str(certstore_path))
        keystore_path = self.certstore = CFG.get_safe('authentication.keystore', KEYSTORE_PATH)
        log.debug("keystore_path: %s" % str(keystore_path))

        if certstore_path and keystore_path:
            if certstore_path == 'directory':
                log.debug("Container.instance.directory: " % str(Container.instance.directory))
                Container.instance.directory.load_authentication()
            else:
                cont_cert_path = os.path.join(certstore_path, CONTAINER_CERT_NAME)
                log.debug("cont_cert_path: %s" % cont_cert_path)
                cont_key_path = os.path.join(keystore_path, CONTAINER_KEY_NAME)
                log.debug("cont_key_path: %s" % cont_key_path)
                root_cert_path = os.path.join(certstore_path, ORG_CERT_NAME)
                log.debug("root_cert_path: %s" % root_cert_path)

                if os.path.exists(cont_cert_path) and os.path.exists(cont_key_path) and os.path.exists(root_cert_path):
                    with open(cont_cert_path, 'r') as f:
                        self.cont_cert = f.read()
                    log.debug("cont_cert: %s" % self.cont_cert)
                    self.cont_key = EVP.load_key(cont_key_path)
                    with open(root_cert_path, 'r') as f:
                        self.root_cert = f.read()
                    log.debug("root_cert: %s" % self.root_cert)
                    self.add_to_white_list(self.root_cert)

    def add_to_white_list(self, root_cert_string):
        log.debug("Adding certificate <%s> to white list" % root_cert_string)
        self.white_list.append(root_cert_string)

    def get_container_cert(self):
        return self.cont_cert

    def authentication_enabled(self):
        if self.cont_key:
            return True
        else:
            return False

    def sign_message_hex(self, message, rsa_private_key=None):
        """
        @param message byte string
        return a hex encoded signature for a message
        """
        return binascii.hexlify(self.sign_message(message, rsa_private_key))

    def sign_message(self, message, rsa_private_key=None):
        """
        take a message, and return a binary signature of it
        """
        hash = hashlib.sha1(message).hexdigest()

        if rsa_private_key:
            pkey = EVP.load_key_string(rsa_private_key)
        else:
            pkey = self.cont_key
        pkey.sign_init()
        pkey.sign_update(hash)
        sig = pkey.sign_final()
        return sig

    def verify_message_hex(self, message, cert_string, signed_message_hex):
        """
        verify a hex encoded signature for a message
        """
        return self.verify_message(message, cert_string, binascii.unhexlify(signed_message_hex))

    def verify_message(self, message, cert_string, signed_message):
        """
        This verifies that the message and the signature are indeed signed by the certificate
        """

        # Check validity of certificate
        status, cause = self.is_certificate_valid(cert_string)
        if status != "Valid":
            log.debug("Message <%s> signed with invalid certificate <%s>. Cause <%s>" % (str(message), cert_string, cause))
            return status, cause

        hash = hashlib.sha1(message).hexdigest()

        # Check validity of signature
        x509 = X509.load_cert_string(cert_string)
        pubkey = x509.get_pubkey()
        pubkey.verify_init()
        pubkey.verify_update(hash)
        outcome = pubkey.verify_final(signed_message)
        if outcome == 1:
            return 'Valid', 'OK'
        else:
            return 'Invalid', 'Signature failed verification'

    def decode_certificate_string(self, cert_string):
        """
        Return a Dict of all known attributes for the certificate
        """
        return self.decode_certificate(X509.load_cert_string(cert_string, format=1))

    def decode_certificate(self, x509):
        """
        Return a Dict of all known attributes for the certificate
        """
        attributes = {}

        attributes['subject_items'] = {}
        attributes['subject'] = str(x509.get_subject())
        for item in attributes['subject'].split('/'):
            try:
                key, value = item.split('=')
                attributes['subject_items'][key] = urllib.unquote(value)
            except:
                """
                """

        attributes['issuer_items'] = {}
        attributes['issuer'] = str(x509.get_issuer())
        for item in attributes['issuer'].split('/'):
            try:
                key, value = item.split('=')
                attributes['issuer_items'][key] = urllib.unquote(value)
            except:
                """
                """

        attributes['not_valid_before'] = str(x509.get_not_before())
        attributes['not_valid_after'] = str(x509.get_not_after())
        attributes['ext_count'] = str(x509.get_ext_count())
        attributes['fingerprint'] = str(x509.get_fingerprint())
        attributes['text'] = str(x509.as_text())
        attributes['serial_number'] = str(x509.get_serial_number())
        attributes['version'] = str(x509.get_version())

        return attributes

    def is_certificate_valid(self, cert_string):
        """
        This returns if the certificate is valid.
        """
        if not self.is_certificate_within_date_range(cert_string):
            return 'Invalid', 'Certificate is not within date range'
        if self.is_certificate_in_white_list(cert_string):
            return 'Valid', 'OK'
        else:
            return 'Invalid', ' Certificate does not derive from any known root certificates'

    def is_certificate_in_white_list(self, cert_string):
        for root_cert in self.white_list:
            if self.is_certificate_descended_from(cert_string, root_cert):
                return True
        return False

    def is_certificate_descended_from(self, cert_string, root_cert):
        """
        tests if the certificate was issued by the passed in certificate authority
        """
        root_cert_attrs = self.decode_certificate_string(root_cert)
        root_subject = root_cert_attrs['subject']

        cert_attrs = self.decode_certificate_string(cert_string)
        cert_issuer = cert_attrs['issuer']

        if root_subject == cert_issuer:
            return True
        return False
#        store = X509.X509_Store()
#        store.add_x509(root_cert)
#        x509 = X509.load_cert_string(cert_string)
#        return X509.X509.verify(x509)

    def is_certificate_within_date_range(self, cert_string):
        """
        Test if the current date is covered by the certificates valid within date range.
        """
        cert = X509.load_cert_string(cert_string)
        nvb = datetime.datetime.strptime(str(cert.get_not_before()), "%b %d %H:%M:%S %Y %Z")
        nva = datetime.datetime.strptime(str(cert.get_not_after()), "%b %d %H:%M:%S %Y %Z")
        now = datetime.datetime.utcnow()

        if now < nvb:
            return False
        if now > nva:
            return False
        return True

