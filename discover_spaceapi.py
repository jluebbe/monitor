#!/usr/bin/python

from urlparse import urlparse

def host_from_url(url):
    assert(isinstance(url, basestring))
    return urlparse(url).hostname

def discover_feeds(c, feeds):
    if "name" in feeds and "url" in feeds:
        n = Feed(name=feeds["url"])
        n.conf["kind"] = feeds["name"]
        c.add(n)
    elif isinstance(feeds, list): # list of feeds
        for props in feeds:
            n = Feed(name=props["url"])
            print n.conf
            n.conf["kind"] = props["name"]
            c.add(n)
    elif isinstance(feeds, dict): # dict of feeds
        for kind, props in feeds.items():
            n = Feed(name=props["url"])
            print props
            n.conf["kind"] = kind
            c.add(n)

def discover_contacts(c, contacts):
    if "email" in contacts:
        try:
            n = EMailAddress(name=contacts["email"])
            n.conf["kind"] = "primary contact"
            c.add(n)
        except ValueError:
            pass
    if "ml" in contacts:
        try:
            n = EMailAddress(name=contacts["ml"])
            n.conf["kind"] = "primary mailing list"
            c.add(n)
        except ValueError:
            pass
    if "twitter" in contacts:
        n = Feed(name="https://twitter.com/%s" % contacts["twitter"].lstrip("@"))
        n.conf["kind"] = "primary twitter feed"
        c.add(n)

def discover(node, data):
    print node
    c = node.children["spaceapi"]
    while c:
        c.pop()
    c = set()
    if "url" in data:
        c.add(HTTPService(name=data["url"]))
        host = host_from_url(data["url"])
        if not host is None:
            c.add(HostName(name=host))
    if "feeds" in data:
        discover_feeds(c, data["feeds"])
    if "contact" in data:
        discover_contacts(c, data["contact"])
    for n in c:
        node.children["spaceapi"].append(n)

from orm import session, SpaceAPI, Result
from orm import HTTPService, HostName, Feed, EMailAddress

if __name__=="__main__":
    for node in session.query(SpaceAPI):
        result = node.results.filter(Result.method=="spaceapi").first()
        if not result or not result.data:
            print "no spaceapi result for %s" % node
            continue
        discover(node, result.data)
    session.commit()

