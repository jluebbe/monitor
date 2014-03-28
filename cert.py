#!/usr/bin/python

import sys
import codecs
from Crypto.Util.asn1 import DerSequence
import hashlib, socket
from OpenSSL import SSL, crypto

from ssl_ca import pin_to_fingerprint, fingerprint_to_pin, fingerprint, add_cert

def HPKP(cert):
    der = crypto.dump_certificate(crypto.FILETYPE_ASN1, cert)
    cert = DerSequence()
    cert.decode(der)
    tbsCertificate = DerSequence()
    tbsCertificate.decode(cert[0])
    subjectPublicKeyInfo = tbsCertificate[6]
    fp = fingerprint(subjectPublicKeyInfo, hashlib.sha1)
    print('HPKP sha1 fp %s' % fp)
    print('HPKP sha1 pin %s' % fingerprint_to_pin(fp))
    fp = fingerprint(subjectPublicKeyInfo, hashlib.sha256)
    print('HPKP sha256 fp %s' % fp)
    print('HPKP sha256 pin %s' % fingerprint_to_pin(fp))

if __name__=="__main__":
    context = SSL.Context(SSL.TLSv1_METHOD)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection = SSL.Connection(context,s)
    connection.connect((sys.argv[1], 443))
    connection.setblocking(1)
    try:
        connection.do_handshake()
    except OpenSSL.SSL.WantReadError:
        print("Timeout")
        quit()

    print(connection.get_peer_certificate().get_subject().commonName)
    print(connection.get_peer_certificate().digest("sha1"))
    for cert in connection.get_peer_cert_chain():
        print(cert)
        print(cert.get_subject())
        print(cert.digest("sha1"))
        print(hashlib.sha1(crypto.dump_certificate(crypto.FILETYPE_ASN1, cert)).hexdigest())
        HPKP(cert)
        add_cert(cert)

    from orm import session

    session.commit()

