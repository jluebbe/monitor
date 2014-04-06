#!/usr/bin/python

NAME = "hostname"

import dns.resolver
import socket
import ipaddr
from pprint import pprint

resolver = dns.resolver.Resolver(configure=False)
resolver.nameservers = ['8.8.8.8']
resolver.cache = dns.resolver.Cache()


def is_ipaddr(x):
    try:
        ipaddr.IPAddress(x)
    except ValueError:
        return False
    return True


def query(*args):
    return resolver.query(*args, tcp=True)


def find_address(hostname):
    result = {"a": [], "aaaa": []}
    try:
        for x in query(hostname, "A"):
            result["a"].append(x.address)
    except dns.exception.DNSException:
        pass
    except socket.error:
        pass
    try:
        for x in query(hostname, "AAAA"):
            result["aaaa"].append(x.address)
    except dns.exception.DNSException:
        pass
    except socket.error:
        pass
    return result


def find_cname(hostname):
    result = {"cname": []}
    try:
        for x in query(hostname, "CNAME"):
            result["cname"].append(str(x.target))
    except dns.exception.DNSException:
        pass
    except socket.error:
        pass
    return result


def find_soa(hostname):
    result = {"soa": ""}
    try:
        query = dns.message.make_query(hostname, dns.rdatatype.SOA)
        response = dns.query.tcp(query, resolver.nameservers[0])
        soa = ""
        if response.answer:
            soa = str(response.answer[0].name)
        elif response.authority:
            soa = str(response.authority[0].name)
        if soa and not soa == ".":
            result["soa"] = soa
    except dns.exception.DNSException:
        pass
    except socket.error:
        pass
    return result


def find_sshfp(hostname):
    result = {"sshfp": []}
    try:
        for x in query(hostname, "SSHFP"):
            result["sshfp"].append((x.algorithm, x.fp_type, x.fingerprint.encode("hex-codec")))
    except dns.exception.DNSException:
        pass
    except socket.error:
        pass
    return result


from orm import session, HostName, Result

if __name__ == "__main__":
    for x in session.query(HostName):
        if not x.is_expired(NAME, age=60 * 60):
            continue
        hostname = x.get_hostname()
        if is_ipaddr(hostname):
            continue
        data = {}
        data.update(find_address(hostname))
        data.update(find_cname(hostname))
        data.update(find_soa(hostname))
        data.update(find_sshfp(hostname))
        x.results.append(Result(NAME, data))
        pprint({hostname: data})
        session.commit()
