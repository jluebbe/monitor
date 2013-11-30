#!/usr/bin/python

import dns.resolver
from pprint import pprint

resolver = dns.resolver.Resolver(configure=False)
resolver.nameservers=['8.8.8.8']
resolver.cache = dns.resolver.Cache()

def query(*args):
  return resolver.query(*args, tcp=True)

def find_basic(hostname):
  result = {"mx": [], "ns": []}
  try:
    for x in query(hostname, "MX"):
      result["mx"].append((str(x.exchange), "tcp", 25))
  except dns.exception.DNSException:
    pass
  try:
    for x in query(hostname, "NS"):
      result["ns"].append((str(x.target), "udp", 53))
  except dns.exception.DNSException:
    pass
  return result

SRV = ["turn"]
SRV_TCP = SRV+["caldav", "caldavs", "carddavs", "imap", "imaps", "pop3", "pop3s", "submission", "xmpp-client", "xmpp-server"]
SRV_UDP = SRV+["sip", "stun"]
def find_srv(hostname):
  result = {}
  for service in SRV_TCP:
    result.setdefault(service, [])
    try:
      for x in query("_%s._tcp.%s" % (service, hostname), "SRV"):
        result[service].append((str(x.target), "tcp", x.port))
    except dns.exception.DNSException:
      pass
  for service in SRV_UDP:
    result.setdefault(service, [])
    try:
      for x in query("_%s._udp.%s" % (service, hostname), "SRV"):
        result[service].append((str(x.target), "udp", x.port))
    except dns.exception.DNSException:
      pass
  return result

def find_dnssd(hostname):
  result = []
  try:
    for x in query("_services._dns-sd._udp.%s" % hostname, "PTR", "IN"):
      result.append(str(x.target))
  except dns.exception.DNSException:
    pass
  return {"dns-sd": result}

def show(hostname):
  data = {}
  data.update(find_basic(hostname))
  data.update(find_srv(hostname))
  data.update(find_dnssd(hostname))
  pprint({hostname: data})

show("dns-sd.org")
show("google.com")
show("stratum0.org")
show("stratum0blalssdf.net")
show("stratum0.net")
show("totalueberwachung.de")
show("sipgate.de")

