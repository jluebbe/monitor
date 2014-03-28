#!/usr/bin/python

NAME = "tlsa"

import dns.resolver
from pprint import pprint
import urlparse

resolver = dns.resolver.Resolver(configure=False)
resolver.nameservers=['8.8.8.8']
resolver.cache = dns.resolver.Cache()

def query(*args):
  return resolver.query(*args, tcp=True)

def find_tlsa(hostname, port):
  result = {"tcp": [], "udp": []}
  try:
    for x in query("_%i._tcp.%s" % (port, hostname), "TLSA"):
      result["tcp"].append((x.usage, x.selector, x.mtype, x.cert.encode("hex-codec")))
  except dns.exception.DNSException:
    pass
  try:
    for x in query("_%i._udp.%s" % (port, hostname), "TLSA"):
      result["udp"].append((x.usage, x.selector, x.mtype, x.cert.encode("hex-codec")))
  except dns.exception.DNSException:
    pass
  return result

from orm import engine, session, Node, Result

if __name__=="__main__":
  engine.echo = False
  for x in session.query(Node):
    if not x.is_expired(NAME, 60*60):
      continue
    url = urlparse.urlsplit(x.name)
    if not url.hostname or not url.port:
      continue
    data = find_tlsa(url.hostname, url.port)
    x.results.append(Result(NAME, data))
    pprint({x.name: data})
    session.commit()

