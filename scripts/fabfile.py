#!/usr/bin/env python

from __future__ import with_statement
from fabric.api import *
import os
import re
import time

ca_config_content = "\
[ req ]\n\
default_bits            = 2048\n\
default_keyfile         = ./private/root.key\n\
default_md              = sha1\n\
prompt                  = no\n\
distinguished_name      = root_ca_distinguished_name\n\
x509_extensions = v3_ca\n\
\n\
[ root_ca_distinguished_name ]\n\
countryName             = US\n\
stateOrProvinceName     = California\n\
localityName            = La Jolla\n\
0.organizationName      = Ocean Observatory Initiative\n\
commonName              = COMMONNAME\n\
emailAddress            = EMAILADDRESS\n\
\n\
[ v3_ca ]\n\
subjectKeyIdentifier=hash\n\
authorityKeyIdentifier=keyid:always,issuer:always\n\
basicConstraints = CA:true\n\
\n\
[ ca ]\n\
default_ca              = CA_default\n\
\n\
[ CA_default ]\n\
dir                     = .\n\
new_certs_dir           = ./signed-keys/\n\
database                = ./conf/index\n\
certificate             = ./public/root.crt\n\
serial                  = ./conf/serial\n\
private_key             = ./private/root.key\n\
x509_extensions         = usr_cert\n\
name_opt                = ca_default\n\
cert_opt                = ca_default\n\
default_crl_days        = 30\n\
default_days            = 365\n\
default_md              = sha1\n\
preserve                = no\n\
policy                  = policy_match\n\
\n\
[ policy_match ]\n\
countryName             = match\n\
stateOrProvinceName     = supplied\n\
organizationName        = supplied\n\
organizationalUnitName  = optional\n\
commonName              = supplied\n\
emailAddress            = optional\n\
\n\
[ usr_cert ]\n\
basicConstraints=CA:FALSE\n\
subjectKeyIdentifier=hash\n\
authorityKeyIdentifier=keyid,issuer:always\n\
nsCaRevocationUrl     = REVOCATIONURL\n\
"

ca_dir = None
def setcadir():
    global ca_dir
    if not ca_dir:
        ca_dir = prompt('Certificate Authority directory: ', default='~/ION_CA')
    if '~' in ca_dir:
        homedir = os.getenv("HOME")
        ca_dir = os.path.join(homedir, ca_dir.strip('~/'))


def mkca():
    setcadir()

    global ca_dir

    # See if any existing directory should be removed
    if os.path.exists(ca_dir):
        do_del = prompt('%s already exists.  Delete? ' % ca_dir, default='Y')
        if do_del == 'Y' or do_del == 'y':
           local('rm -rf %s' % ca_dir)

    local('rm -rf %s' % ca_dir)

    # Make root CA directory
    local('mkdir -m 0755 %s' % ca_dir)

    # Make necessary subdirectories
    local('cd %s;mkdir -m 0755 conf private public signed-keys' % ca_dir)

    # Substitute values into template config file
    rootca_common_name = prompt('Certificate Authority common name: ', default='Ocean Observatory Initiative Root CA')
    rootca_email_address = prompt('Certificate Authority email address: ', default='owen_ownerrep@google.com')
    revocation_url = prompt('Revocation URL: ', default='https://security.oceanobservatories.org/revoke')

    o_path = os.path.join(ca_dir,"conf/openssl.cnf")
    o = open(o_path, 'w+')

    openssl_cnf = ca_config_content
    openssl_cnf = re.sub('COMMONNAME', rootca_common_name, openssl_cnf)
    openssl_cnf = re.sub('EMAILADDRESS', rootca_email_address, openssl_cnf)
    openssl_cnf = re.sub('REVOCATIONURL', revocation_url, openssl_cnf)

    o.write(openssl_cnf)
    o.close()

    # Copy config file to root CA directory
    local('chmod 0600 %s/conf/openssl.cnf' % ca_dir)

    # Set up extra files required by OpenSSL for certificate signing
    local("echo '01' > %s/conf/serial" % ca_dir)
    local('touch %s/conf/index' % ca_dir)
 

def mkrootcert():
    setcadir()

    global ca_dir
    local('cd %s;openssl req -nodes -config conf/openssl.cnf -days 1825 -x509 -newkey rsa:1024 -out public/root.crt -outform PEM' % ca_dir)
    print '#######################################'
    print '#######################################'
    print 'You can now copy file %s/private/root.crt to the keystore' % (ca_dir)
    print '#######################################'
    print '#######################################'

def mkcontainercert():
    setcadir()

    global ca_dir
    key_duration = prompt('Key duration: ', default='365')
    key_filename = prompt('Key and CRT filename prefix: ', default='container')
    # Create private key and CSR
    local('cd %s;openssl req -config conf/openssl.cnf -new -nodes -keyout private/%s.key -out public/%s.csr -outform PEM -days %s' % (ca_dir, key_filename, key_filename, key_duration))
    # Sign the CSR
    local('cd %s;openssl ca -batch -config conf/openssl.cnf -in public/%s.csr -out public/%s.crt' % (ca_dir, key_filename, key_filename))
    # For grins, validate the signed certificate
    local('cd %s;openssl verify -purpose sslserver -CAfile public/root.crt public/%s.crt' % (ca_dir, key_filename))
    print '#######################################'
    print '#######################################'
    print 'You can now copy files %s/public/%s.key and %s/private/%s.crt to the keystore' % (ca_dir, key_filename, ca_dir, key_filename)
    print '#######################################'
    print '#######################################'
