#!/usr/bin/python

from urlparse import urlparse

from orm import session, DomainName, Result
from orm import MailServer, NameServer, XMPPServer

def discover(node, data):
    print node
    c = node.children["services"]
    existing = set((x.__class__, x.name) for x in c)
    print existing
    current = set()
    for name, proto, port in data.get("mx", []):
        current.add((MailServer, "smtp://%s:%i" % (name, port)))
    for name, proto, port in data.get("ns", []):
        current.add((NameServer, name))
    for name, proto, port in data.get("xmpp-client", []):
        current.add((XMPPServer, "xmpp-client://%s:%i" % (name, port)))
    for name, proto, port in data.get("xmpp-server", []):
        current.add((XMPPServer, "xmpp-server://%s:%i" % (name, port)))
    new = current - existing
    for x in new:
        c.append(x[0](name=x[1]))

for node in session.query(DomainName):
    result = node.results.filter(Result.method=="domainname").first()
    if not result or not result.data:
        print "no domainname result for %s" % node
        continue
    discover(node, result.data)

session.commit()

