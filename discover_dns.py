#!/usr/bin/python

from urlparse import urlparse

def discover(node, data):
    print node
    c = node.children["dns"]
    existing = set((x.__class__, x.name) for x in c)
    print existing
    current = set()
    for name in data.get("cname", []):
        current.add((HostName, name))
    name = data.get("soa")
    if name:
        current.add((DomainName, name))
    new = current - existing
    for x in new:
        c.append(x[0](name=x[1]))

from orm import session, HostName, DomainName, Result

if __name__=="__main__":
    for node in session.query(HostName):
        result = node.results.filter(Result.method=="hostname").first()
        if not result or not result.data:
            print "no hostname result for %s" % node
            continue
        discover(node, result.data)
    session.commit()

