#!/usr/bin/python

from urlparse import urlparse

def discover(node, data):
    print node
    c = node.children["spaceapidirectory"]
    existing = set(x.name for x in c if isinstance(x, SpaceAPI))
    current = set(x for x in data.values())
    new = current - existing
    for x in new:
        c.append(SpaceAPI(name=x))

from orm import session, JSONAPI, SpaceAPI, Result

if __name__=="__main__":
    for node in session.query(JSONAPI):
        if not node.conf["discover"] == "spaceapidirectory":
            continue
        result = node.results.filter(Result.method=="jsonapi").first()
        if result is None:
            print "no jsonapi result for %s" % node
            continue
        discover(node, result.data)
        session.commit()

