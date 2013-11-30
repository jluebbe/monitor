#!/usr/bin/python

import dns.resolver
from pprint import pprint

def find_basic(hostname):
  result = {"mx": [], "ns": []}
  try:
    for x in dns.resolver.query(hostname, "MX"):
      result["mx"].append((str(x.exchange), "tcp", 25))
  except dns.exception.DNSException:
    pass
  try:
    for x in dns.resolver.query(hostname, "NS"):
      result["ns"].append((str(x.target), "udp", 53))
  except dns.exception.DNSException:
    pass
  return result

SRV = ["turn"]
SRV_TCP = SRV+["imap", "imaps", "pop3", "pop3s", "submission", "xmpp-client", "xmpp-server"]
SRV_UDP = SRV+["sip", "stun"]
def find_srv(hostname):
  result = {}
  for service in SRV_TCP:
    result.setdefault(service, [])
    try:
      for x in dns.resolver.query("_%s._tcp.%s" % (service, hostname), "SRV"):
        result[service].append((str(x.target), "tcp", x.port))
    except dns.exception.DNSException:
      pass
  for service in SRV_UDP:
    result.setdefault(service, [])
    try:
      for x in dns.resolver.query("_%s._udp.%s" % (service, hostname), "SRV"):
        result[service].append((str(x.target), "udp", x.port))
    except dns.exception.DNSException:
      pass
  return result

def show(hostname):
  data = {}
  data.update(find_basic(hostname))
  data.update(find_srv(hostname))
  pprint({hostname: data})

show("stratum0.org")
show("stratum0blalssdf.net")
show("stratum0.net")
show("totalueberwachung.de")
show("sipgate.de")

