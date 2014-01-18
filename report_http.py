#!/usr/bin/python

from urlparse import urlparse

def has_hsts(headers):
    if not 'strict-transport-security' in headers:
        return False
    # FIXME check max-age
    return True

def report(url, headers):
    print "  " + repr(headers)
    url = urlparse(url)
    if "location" in headers:
        location = urlparse(headers["location"])
    if url.scheme=="http":
        if headers["status"] in [301, 302] and \
            location.scheme=="https":
            print " +1 HTTP to HTTPS redirect"
        else:
            print " -1 HTTP (unencrypted)"
    elif url.scheme=="https":
        print " +1 HTTPS (encrypted)"
        if has_hsts(headers):
            print " +5 HSTS enabled"

from orm import engine, Base, HTTPService, Result

engine.echo = False

for x in Base.query(HTTPService):
    url = x.name
    print url
    result = x.results.filter(Result.method=="httpservice").first()
    if result:
        headers = result.data
        report(url, headers)

