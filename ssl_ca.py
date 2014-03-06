#!/usr/bin/python

BASE = "/etc/ssl/certs"

import codecs
import os
import sys
from Crypto.Util.asn1 import DerSequence
import hashlib, socket
from OpenSSL import crypto

def pin_to_fingerprint(pin):
    return ":".join(c.encode("hex") for c in pin.decode("base64"))
 
def fingerprint_to_pin(fingerprint):
    x = fingerprint.replace(":","")
    x = codecs.decode(x, "hex_codec")
    x = codecs.encode(x, "base64_codec")
    return x.strip().decode("ascii")

def fingerprint(spki, hash):
    """Calculate fingerprint of a SubjectPublicKeyInfo given a hash function."""
    return ":".join("%02x" % c for c in bytearray(hash(spki).digest()))

def load_cert(filename):
    pem = open(filename, "r").read()
    return crypto.load_certificate(crypto.FILETYPE_PEM, pem)

from orm import session, SSLCert

def add_cert(cert, is_anchor=False):
    #print(cert)
    print(cert.get_subject(), '%08x' % cert.get_subject().hash(), fingerprint(cert.get_subject().der(), hashlib.md5))
    #print(cert.get_subject().get_components())
    #print(cert.digest("sha1"))
    #print(hashlib.sha1(crypto.dump_certificate(crypto.FILETYPE_ASN1, cert)).hexdigest())

    subject = repr(cert.get_subject().get_components())
    subject_der = cert.get_subject().der()
    data_der = crypto.dump_certificate(crypto.FILETYPE_ASN1, cert)
    result = session.query(SSLCert).filter_by(subject_der=subject_der, data_der=data_der).first()
    if result:
        print "already have %s: %s" % (subject, result)
        return result
    x = SSLCert()
    x.is_anchor = is_anchor
    x.subject = subject
    x.subject_der = subject_der
    x.data_der = data_der
    session.add(x)
    return x

if __name__=="__main__":
    for name in os.listdir(BASE):
        name = os.path.join(BASE, name)
        if not name.endswith('.pem'):
            continue
        if not os.path.isfile(name):
            continue

        cert = load_cert(name)
        add_cert(cert, is_anchor=True)
        session.commit()

