#!/usr/bin/python

import sys
import codecs
from Crypto.Util import asn1
import hashlib, socket
from OpenSSL import SSL, crypto

def verify(cert, cacert):
    print "cacert notBefore", cacert.get_notBefore()
    print "cacert notAfter", cacert.get_notAfter()

    # Get the signing algorithm
    algo=cert.get_signature_algorithm()
     
    # Get the ASN1 format of the certificate
    cert_asn1=crypto.dump_certificate(crypto.FILETYPE_ASN1, cert)
     
    # Decode the certificate
    der=asn1.DerSequence()
    der.decode(cert_asn1)
     
    # The certificate has three parts:
    # - certificate
    # - signature algorithm
    # - signature
    # http://usefulfor.com/nothing/2009/06/10/x509-certificate-basics/
    der_cert=der[0]
    der_algo=der[1]
    der_sig=der[2]
     
    # The signature is a BIT STRING (Type 3)
    # Decode that as well
    der_sig_in=asn1.DerObject()
    der_sig_in.decode(der_sig)
     
    # Get the payload
    sig0=der_sig_in.payload
     
    # Do the following to see a validation error for tests
    # der_cert=der_cert[:20]+'1'+der_cert[21:]
     
    # First byte is the number of unused bits. This should be 0
    # http://msdn.microsoft.com/en-us/library/windows/desktop/bb540792(v=vs.85).aspx
    if sig0[0]!='\x00':
        raise Exception('Number of unused bits is strange')
     
    # Now get the signature itself
    sig=sig0[1:]
     
    # And verify the certificate
    print algo
    try:
        crypto.verify(cacert, sig, der_cert, algo)
        print "Certificate looks good"
    except crypto.Error as e:
        print "Sorry. Nope."
#    except ValueError as e: # algo "ecdsa-with-SHA384" seems to be unsupported
#        print e

from ssl_ca import pin_to_fingerprint, fingerprint_to_pin, fingerprint, load_cert

from orm import engine, session, SSLCert

engine.echo = False

for cert in session.query(SSLCert):
    cert_x509 = crypto.load_certificate(crypto.FILETYPE_ASN1, cert.data_der)
    subject_name = repr(cert_x509.get_subject().get_components())
    subject_der = cert_x509.get_subject().der()
    issuer_name = repr(cert_x509.get_issuer().get_components())
    issuer_der = cert_x509.get_issuer().der()
    if cert.is_anchor and subject_der==issuer_der:
        print "Skipping self signed root cert"
        cert.issuer_id = cert.id
        continue
    results = session.query(SSLCert).filter_by(subject_der=issuer_der).all()
    if not results:
        cert.issuer_id = None
        if cert.is_anchor:
            continue
        print "Issuer not found"
        print subject_name, issuer_name
        continue
    if len(results)>1:
        cert.issuer_id = None
        print "Multiple issuers found"
    print subject_name, issuer_name
    for cacert in results:
        print "Issuer:", cacert
        cacert_x509 = crypto.load_certificate(crypto.FILETYPE_ASN1, cacert.data_der)
        verify(cert_x509, cacert_x509) 
        cert.issuer_id = results[0].id

session.commit()

