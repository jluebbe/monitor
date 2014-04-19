#!/usr/bin/python

NAME = "ssl"

import urlparse
import socket
import time
from OpenSSL import SSL

from ssl_ca import add_cert


def starttls_smtp(s, servername):
    buf = ""
    while not ("220" in buf and "\r\n" in buf):
        time.sleep(0.1)
        buf += s.recv(1024)
    buf = ""
    s.send("EHLO %s\r\n" % ("jluebbe.github.io",))
    starttls = False
    while True:
        if '\r\n' in buf:
            line, buf = buf.split('\r\n', 1)
            if 'STARTTLS' in line:
                starttls = True
            if line[3] == ' ':
                break
            continue
        time.sleep(0.1)
        buf += s.recv(1024)
    if not starttls:
        return False
    s.send("STARTTLS\n")
    buf = ""
    while not ("220" in buf and "\r\n" in buf):
        time.sleep(0.1)
        buf += s.recv(1024)
    return True


def starttls_xmpp(s, servername):
    buf = ""
    s.send("<stream:stream xmlns:stream='http://etherx.jabber.org/streams' xmlns='jabber:client' to='%s' version='1.0'>" % (servername,))
    while not "</stream:features>" in buf:
        if "</stream:stream>" in buf:
            return False
        time.sleep(0.1)
        buf += s.recv(1024)
    if not "<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'>" in buf:
        return False
    s.send("<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
    buf = ""
    while not "<proceed" in buf:
        if "</stream:stream>" in buf:
            return False
        time.sleep(0.1)
        buf += s.recv(1024)
    return True


def fetch(host, port, scheme, servername=None):
    if servername is None:
        servername = host
    context = SSL.Context(SSL.TLSv1_METHOD)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except socket.gaierror:
        return {}
    if scheme in ['smtp']:
        if not starttls_smtp(s, servername):
            return {}
    elif scheme in ['xmpp-client', 'xmpp-server']:
        if not starttls_xmpp(s, servername):
            return {}
    connection = SSL.Connection(context, s)
    connection.set_connect_state()
    connection.set_tlsext_host_name(host)
    connection.setblocking(1)
    try:
        connection.do_handshake()
    except SSL.WantReadError:
        connection.close()
        return {}
    chain = []
    for cert in connection.get_peer_cert_chain():
        c = add_cert(cert)
        chain.append((c.subject, c.data_hash()))
    return {'chain': chain}

from orm import session, HTTPService, Result

if __name__ == "__main__":
    for x in HTTPService.query:
        print x.name
        if not x.is_expired(NAME, age=60 * 60):
            continue
        url = urlparse.urlparse(x.name)
        if url.scheme in ['smtp', 'https', 'xmpp-client']:
            x.results.append(Result(NAME, fetch(url.hostname, url.port or 443), url.scheme))
        else:
            continue
        session.commit()
