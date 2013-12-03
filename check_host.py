#!/usr/bin/python

import dns.resolver
from pprint import pprint

resolver = dns.resolver.Resolver(configure=False)
resolver.nameservers=['8.8.8.8']
resolver.cache = dns.resolver.Cache()

def query(*args):
  return resolver.query(*args, tcp=True)

def find_address(hostname):
  result = {"a": [], "aaaa": []}
  try:
    for x in query(hostname, "A"):
      result["a"].append(x.address)
  except dns.exception.DNSException:
    pass
  try:
    for x in query(hostname, "AAAA"):
      result["aaaa"].append(x.address)
  except dns.exception.DNSException:
    pass
  return result

def find_cname(hostname):
  result = {"cname": []}
  try:
    for x in query(hostname, "CNAME"):
      result["cname"].append(str(x.target))
  except dns.exception.DNSException:
    pass
  return result

from orm import session, HostName, Result

for x in session.query(HostName):
    hostname = x.name
    data = {}
    data.update(find_address(hostname))
    data.update(find_cname(hostname))
    x.results.append(Result("hostname", data))
    session.commit()
    pprint({hostname: data})

