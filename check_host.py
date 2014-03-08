#!/usr/bin/python

NAME = "hostname"

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

def find_soa(hostname):
  result = {"soa": ""}
  try:
    query = dns.message.make_query(hostname, dns.rdatatype.SOA)
    response = dns.query.tcp(query, resolver.nameservers[0])
    if response.answer:
      result["soa"] = str(response.answer[0].name)
    elif response.authority:
      result["soa"] = str(response.authority[0].name)
  except dns.exception.DNSException:
    pass
  return result

from orm import session, HostName, Result

for x in session.query(HostName):
    if not x.is_expired(NAME):
        continue
    hostname = x.get_hostname()
    data = {}
    data.update(find_address(hostname))
    data.update(find_cname(hostname))
    data.update(find_soa(hostname))
    x.results.append(Result(NAME, data))
    pprint({hostname: data})
    session.commit()

