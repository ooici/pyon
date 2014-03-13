#!/usr/bin/env python

from nose.plugins.attrib import attr
from unittest import skip

from pyon.util.unit_test import PyonTestCase
from pyon.core.security.authentication import Authentication


@attr('UNIT',group='coi')
class AuthenticationTest(PyonTestCase):

    def setUp(self):
        pass

    @skip("Authentication test CERTIFICATE expired - please fix me!!")
    def test_authentication(self):
        private_key = """
-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDELieVJmWlcD1qfumxhraYailqB9Wd9emCLtSDPRRNAbSvOrTd
+YVHvdC6xMG1JykFRUld4oWcHW7VGDVeiERAlUnfeJ/gK5/UkfUlJWqEOL7Hks9B
lN7ls+1E94lGdDZ4hFl56k/rC7ERt8Z88ogZACirXEW6QG3C+dhO2XA3ZwIDAQAB
AoGARyIBIjiY9KK88idwbvlMrfkYaSTMFQl8kMKQNcHo4X8z17GusSnvZLLzwzTi
k9/OJOYZkxw2nAOkE0pC17MLI8inO9gljv3jfdbpJ07iOkDHQ8AUEBRyJKdkG1BP
Xx1uCVnxocihni66w0VPM50X66LQsB2Tujei7PI1e3l4rckCQQDzsdzXykNGwrr5
j7XMKWAwrzCRKciBhnk0JDwxDKE7fV7f+KpbgBd3sfgOzSg+or33tpRXHOia284i
K+TpuB6NAkEAzhYXuoNWbDNGy3Bjh7wBg7rdaldFCUft4LPFfj8HnS4bzsUybhm7
SrrESyr8FJbNKmCVn0fIa82yjfAofZk6wwJABet0KenH6JgiYp2TFPqMU6Jt05jo
Pf0+RH382FQuNnu9KkOoH8Dk0QuJsxJYv+zEIJhW0ibpn5lnUH0welz2oQJBAJRu
/yo8XKvUBuKSkW17MVAS8FUehD/aCfB1KwLyHObOBgNYryjz6Z06hhVp4WRm9WDX
bgzqI+XZowhueIt2KQcCQQDNQIhcZduGlG9n//w+MmZ2NuRzW8nANTgS9Ds759vJ
qBkRbsUcWgYKXN4RIqpc1Gjbsb4ltyprCOM35s5v8Ggc
-----END RSA PRIVATE KEY-----
"""
        certificate_crt = """
-----BEGIN CERTIFICATE-----
MIICPzCCAagCCQCRkPH0fJqEzzANBgkqhkiG9w0BAQUFADBkMQswCQYDVQQGEwJB
VTELMAkGA1UECBMCQ0ExEjAQBgNVBAcTCVNhbiBEaWVnbzEOMAwGA1UEChMFT09J
Q0kxETAPBgNVBAMTCFRoZSBEdWRlMREwDwYJKoZIhvcNAQkBFgJOQTAeFw0xMzAx
MTAwMTM2NTlaFw0xNDAxMTAwMTM2NTlaMGQxCzAJBgNVBAYTAkFVMQswCQYDVQQI
EwJDQTESMBAGA1UEBxMJU2FuIERpZWdvMQ4wDAYDVQQKEwVPT0lDSTERMA8GA1UE
AxMIVGhlIER1ZGUxETAPBgkqhkiG9w0BCQEWAk5BMIGfMA0GCSqGSIb3DQEBAQUA
A4GNADCBiQKBgQDELieVJmWlcD1qfumxhraYailqB9Wd9emCLtSDPRRNAbSvOrTd
+YVHvdC6xMG1JykFRUld4oWcHW7VGDVeiERAlUnfeJ/gK5/UkfUlJWqEOL7Hks9B
lN7ls+1E94lGdDZ4hFl56k/rC7ERt8Z88ogZACirXEW6QG3C+dhO2XA3ZwIDAQAB
MA0GCSqGSIb3DQEBBQUAA4GBAAerq2XzxvcRZ8mskIKTjf/C+B4t2fiCp1lF/ca4
7FxJqmOLvoSJm0eVM0kt67WWy+IeCijctVv1BNhs/FpzaAWKAGjcR36QYpjhjqKs
uCCjrh18zMGpSfKGCoEXb9xKp45UrREqpcbWGYdf3NabKeZSfTXUcxocLh7dtgSS
hEct
-----END CERTIFICATE-----
"""
        certificate_csr = """
-----BEGIN CERTIFICATE REQUEST-----
MIIBuTCCASICAQAwZDELMAkGA1UEBhMCQVUxCzAJBgNVBAgTAkNBMRIwEAYDVQQH
EwlTYW4gRGllZ28xDjAMBgNVBAoTBU9PSUNJMREwDwYDVQQDEwhUaGUgRHVkZTER
MA8GCSqGSIb3DQEJARYCTkEwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAMQu
J5UmZaVwPWp+6bGGtphqKWoH1Z316YIu1IM9FE0BtK86tN35hUe90LrEwbUnKQVF
SV3ihZwdbtUYNV6IRECVSd94n+Arn9SR9SUlaoQ4vseSz0GU3uWz7UT3iUZ0NniE
WXnqT+sLsRG3xnzyiBkAKKtcRbpAbcL52E7ZcDdnAgMBAAGgFTATBgkqhkiG9w0B
CQcxBhMEcGFzczANBgkqhkiG9w0BAQUFAAOBgQBmjsWSCpEv0O76KUv/XArsm9QM
7B6xKxpivLFWh8cOgTdQDhucokoLDQ2NLgVYGgmxy+DSswatFSwK+KEe5Zdafri8
WY8o9L2q/6JOlxJk4vC2pgtEVxomMW1nVH2oepIkT3xLbBVCSVGZcRiY7joueR/J
fLCIe24piwAfVhpMcQ==
-----END CERTIFICATE REQUEST-----
"""
        message = "the dude abides"
        a = Authentication()
        certificate = certificate_crt
        a.add_to_white_list(certificate)

        status = a.authentication_enabled()
        self.assertTrue(status == True or status == False)
        signed_hex = a.sign_message_hex(message, private_key)
        v, ok = a.verify_message_hex(message, certificate, signed_hex)
        self.assertEqual(v, "Valid")
        self.assertEqual(ok, "OK")

        signed = a.sign_message(message, private_key)
        v, ok = a.verify_message(message, certificate, signed)
        self.assertEqual(v, "Valid")
        self.assertEqual(ok, "OK")

        decoded_cert = a.decode_certificate_string(certificate)
        self.assertEqual(decoded_cert['subject_items']['CN'], "The Dude")
