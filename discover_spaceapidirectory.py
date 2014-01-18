#!/usr/bin/python

from urlparse import urlparse

from orm import session, JSONAPI, SpaceAPI, Result

def discover(node, data):
    print node
    existing = set(x.name for x in node.children if isinstance(x, SpaceAPI))
    current = set(x for x in data.values())
    new = current - existing
    for x in new:
        node.children.append(SpaceAPI(name=x))

for node in session.query(JSONAPI):
    if not node.conf["discover"] == "spaceapidirectory":
        continue
    result = node.results.filter(Result.method=="jsonapi").first()
    if result is None:
        print "no jsonapi result for %s" % node
        continue
    discover(node, result.data)
    session.commit()

