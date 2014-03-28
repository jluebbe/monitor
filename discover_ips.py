#!/usr/bin/python

def discover(node, data):
    print node
    c = node.children["ips"]
    existing = set((x.__class__, x.name) for x in c)
    print existing
    current = set()
    for address in data.get("a", []):
        current.add((IP4Address, address))
    for address in data.get("aaaa", []):
        current.add((IP6Address, address))
    new = current - existing
    for x in new:
        c.append(x[0](name=x[1]))

from orm import session, HostName, Result
from orm import IP4Address, IP6Address

if __name__=="__main__":
    for node in session.query(HostName):
        result = node.results.filter(Result.method=="hostname").first()
        if not result or not result.data:
            print "no hostname result for %s" % node
            continue
        discover(node, result.data)
    session.commit()

