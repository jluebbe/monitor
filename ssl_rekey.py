#!/usr/bin/python

import sys
import codecs
from Crypto.Util import asn1
import hashlib
import socket
from OpenSSL import SSL, crypto
from M2Crypto import X509 as M2X509


def get_spki(cert_der):
    cert = M2X509.load_cert_der_string(cert_der)
    spki = cert.get_pubkey()
    return spki.as_der()


def hex(digest):
    return ":".join("%02x" % c for c in bytearray(digest))


def rekey(cert):
    existing = dict((x.key, x) for x in cert.keys)

    cert_x509 = crypto.load_certificate(crypto.FILETYPE_ASN1, cert.data_der)
    pub_der = crypto.dump_privatekey(crypto.FILETYPE_ASN1, cert_x509.get_pubkey())
    subject_der = cert_x509.get_subject().der()
    issuer_der = cert_x509.get_issuer().der()

    keys = set()

    # keys.add("sha1/%s" % hex(hashlib.sha1(cert.data_der).digest()))
    # keys.add("sha256/%s" % hex(hashlib.sha256(cert.data_der).digest()))
    keys.add("sha1/%s" % hashlib.sha1(cert.data_der).hexdigest())
    keys.add("sha256/%s" % hashlib.sha256(cert.data_der).hexdigest())

    keys.add("sub/md5/%s" % hashlib.md5(subject_der).hexdigest())
    keys.add("sub/sha1/%s" % hashlib.sha1(subject_der).hexdigest())

    spki = get_spki(cert.data_der)
    digest = hashlib.sha1(spki).digest()
    # keys.add("hpkp/fp/sha1/%s" % digest.encode("hex_codec"))
    # keys.add("hpkp/pin/sha1/%s" % digest.encode("base64_codec").strip())
    digest = hashlib.sha256(spki).digest()
    keys.add("hpkp/fp/sha256/%s" % digest.encode("hex_codec"))
    keys.add("hpkp/pin/sha256/%s" % digest.encode("base64_codec").strip())

    print keys

    for key in keys:
        if not key in existing:
            cert.keys.append(SSLKey(key))

    for k, v in existing.items():
        if not k in keys:
            cert.keys.remove(v)

from orm import engine, session, SSLCert, SSLKey

if __name__ == "__main__":
    # engine.echo = False
    for cert in session.query(SSLCert):
        print cert
        rekey(cert)
    session.commit()
