#!/usr/bin/python

NAME = "ssl"

import urlparse
import socket
import time
from OpenSSL import SSL

from ssl_ca import add_cert


def starttls_smtp(s, servername):
    buf = ""
    while not "\r\n" in buf:
        if "\r\n" in buf and not buf.startswith("220 "):
            return False
        time.sleep(0.1)
        buf += s.recv(1024)
        if not buf:
            return False
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
        if not buf:
            return False
    if not starttls:
        return False
    s.send("STARTTLS\n")
    buf = ""
    while not "\r\n" in buf:
        if "\r\n" in buf and not buf.startswith("220 "):
            return False
        time.sleep(0.1)
        buf += s.recv(1024)
        if not buf:
            return False
    return True


def starttls_xmpp(s, servername):
    buf = ""
    s.send("<stream:stream xmlns:stream='http://etherx.jabber.org/streams' xmlns='jabber:client' to='%s' version='1.0'>" % (servername,))
    while not "</stream:features>" in buf:
        if "</stream:stream>" in buf:
            return False
        time.sleep(0.1)
        buf += s.recv(1024)
        if not buf:
            return False
    if not "<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'>" in buf:
        return False
    s.send("<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
    buf = ""
    while not "<proceed" in buf:
        if "</stream:stream>" in buf:
            return False
        time.sleep(0.1)
        buf += s.recv(1024)
        if not buf:
            return False
    return True


def starttls(s, servername, scheme):
    if scheme in ['smtp']:
        return starttls_smtp(s, servername)
    elif scheme in ['xmpp-client', 'xmpp-server']:
        return starttls_xmpp(s, servername)
    return True


def fetch(host, port, scheme, servername=None):
    if servername is None:
        servername = host
    context = SSL.Context(SSL.TLSv1_METHOD)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(1)
    s.settimeout(10.0)
    try:
        s.connect((host, port))
        if not starttls(s, servername, scheme):
            return {}
    except (socket.error, socket.gaierror):
        return {}
    connection = SSL.Connection(context, s)
    connection.set_connect_state()
    connection.set_tlsext_host_name(host)
    try:
        connection.do_handshake()
    except (SSL.WantReadError, SSL.Error):
        connection.close()
        return {}
    chain = []
    for cert in connection.get_peer_cert_chain():
        c = add_cert(cert)
        chain.append((c.subject, c.data_hash()))
    return {'chain': chain}

from orm import session, Node, Result

if __name__ == "__main__":
    for x in Node.query:
        print x.name
        if not x.is_expired(NAME, age=60 * 60 * 24 * 5):
            continue
        url = urlparse.urlparse(x.name)
        if url.scheme in ['smtp', 'https', 'xmpp-client']:
            x.results.append(Result(NAME, fetch(url.hostname, url.port, url.scheme)))
        else:
            continue
        session.commit()
