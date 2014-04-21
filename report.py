#!/usr/bin/python

from urlparse import urlparse
from functools import wraps
import orm
from orm import engine, Node, Result
import hashlib


class Registy(type):
    _seq = -1

    @classmethod
    def seq(cls):
        cls._seq += 1
        return cls._seq

    def __init__(cls, name, bases, attrs):
        cls.registry = []
        for key, val in attrs.iteritems():
            props = getattr(val, 'register', None)
            if props is not None:
                cls.registry.append((val,) + props)
        cls.registry.sort(key=lambda x: getattr(x[0], 'seq'))

def register(*args):
    def decorator(f):
        f.register = tuple(args)
        f.seq = Registy.seq()
        return f
    return decorator


def depends(result):
    def decorator(f):
        @wraps(f)
        def wrapper(self, *args):
            if not result in self.results:
                return
            return f(self, *args)
        return wrapper
    return decorator


def hint(category):
    def decorator(f):
        @wraps(f)
        def wrapper(self, *args):
            x = self.hints.setdefault(category, {})
            return f(self, x, *args)
        return wrapper
    return decorator


class Reporter(object):
    __metaclass__ = Registy

    def __init__(self, node):
        self.node = node
        self.results = set()
        self.hints = {}

        for func, cls, method in self.registry:
            if not isinstance(node, cls):
                continue
            r = node.results.filter(Result.method == method).first()
            if not r or not r.data:
                self.results.add("no result for %s" % method)
                continue
            x = func(self, r.data)
            # print func, cls, method, x
            if x:
                self.results.add(x)

    @register(orm.HTTPService, "httpservice")
    def _http_scheme(self, headers):
        url = urlparse(self.node.name)
        if url.scheme == "http":
            return "HTTP (unencrypted)"
        elif url.scheme == "https":
            return "HTTPS (encrypted)"

    @register(orm.HTTPService, "httpservice")
    @depends("HTTP (unencrypted)")
    def _http_status(self, headers):
        if headers["status"] in [301, 302]:
            location = urlparse(headers["location"])
            if location.scheme == "https":
                return "HTTP to HTTPS redirect"

    @register(orm.HTTPService, "httpservice")
    def _http_hsts(self, headers):
        if 'strict-transport-security' in headers:
            return "HSTS enabled"

    @register(orm.HostName, "hostname")
    def _host_ipv6(self, data):
        if 'aaaa' in data and data['aaaa']:
            return "IPv6 supported"

    @register(orm.HostName, "hostname")
    @hint("sshfp")
    def _host_sshfp(self, hint_sshfp, data):
        if 'sshfp' in data and data['sshfp']:
            hint_sshfp['record'] = data['sshfp']
            return "SSHFP supported"

    @register(orm.HostName, "ssh")
    @depends("SSHFP supported")
    @hint("sshfp")
    def _host_sshfp_good(self, hint_sshfp, data):
        # http://tools.ietf.org/html/rfc4255
        if not hint_sshfp:
            return
        for key_alg, hash_alg, dig in hint_sshfp['record']:
            if dig == hashlib.sha1(data['rsa-pkey'].decode('base64-codec')).hexdigest():
                return "SSHFP good"

    @register(orm.HostName, "ssh")
    def _host_ssh_key(self, data):
        return "SSH key size %i bits" % data['rsa-bits']

    @register(orm.HostName, "dnssec")
    def _host_ssh_key(self, data):
        if data.get('secure', 0):
            return "DNSSEC enabled"

    @register(orm.HTTPService, "tlsa")
    @hint("tlsa")
    def _http_tlsa_record(self, hint_tlsa, data):
        keys = []
        for usage, selector, match, val in data["tcp"]:
            if selector == 0: # full certificate
                key = ""
            elif selector == 1: # SubjectPublicKeyInfo
                key = "hpkp/fp/"
            else:
                raise NotImplementedError()
            if match == 0: # exact match
                raise NotImplementedError()
            elif match == 1: # SHA256
                key += "sha256/"
            elif match == 2: # SHA512
                key += "sha512/"
            else:
                raise NotImplementedError()
            key += val
            if usage == 0: # "CA constraint"
                raise NotImplementedError()
            elif usage == 1: # "service certificate constraint"
                raise NotImplementedError()
            elif usage == 2: # "trust anchor assertion"
                raise NotImplementedError()
            elif usage == 3: # "domain-issued certificate"
                keys.append(("=", key))
            else:
                raise NotImplementedError()
        if keys:
            print(keys)
            hint_tlsa['keys'] = keys
            return "TLSA supported"

    @register(orm.HTTPService, "ssl")
    @hint("tlsa")
    def _http_tlsa_ssl(self, hint_tlsa, data):
        keys = hint_tlsa.get('keys', [])
        resolved = data.get("resolved")
        print keys, resolved
        if not resolved:
            return
        for match, key in keys:
            if match == "=":
                if key == resolved[0][-1]:
                    return "TLSA good"
                else:
                    return "TLSA bad"
            else:
                raise NotImplementedError()


if __name__ == "__main__":
    engine.echo = False
    for x in Node.query:
        res = Reporter(x).results
        if res:
            print x
            print '  ', res
