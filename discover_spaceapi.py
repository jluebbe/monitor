#!/usr/bin/python

from urlparse import urlparse

from orm import session, SpaceAPI, Result
from orm import HTTPService, HostName

def host_from_url(url):
  assert(isinstance(url, basestring))
  return urlparse(url).hostname

def discover(node, data):
    print node
    c = node.children["spaceapi"]
    existing = set((x.__class__, x.name) for x in c)
    print existing
    current = set()
    if "url" in data:
        current.add((HTTPService, data["url"]))
        host = host_from_url(data["url"])
        if not host is None:
            current.add((HostName, host))
    new = current - existing
    for x in new:
        c.append(x[0](name=x[1]))

for node in session.query(SpaceAPI):
    result = node.results.filter(Result.method=="spaceapi").first()
    if not result or not result.data:
        print "no spaceapi result for %s" % node
        continue
    discover(node, result.data)

session.commit()

