#!/usr/bin/python

NAME = "dnssec"

import unbound
from unbound import ub_ctx, ub_strerror
import ipaddr
from pprint import pprint


ctx = ub_ctx()
# ctx.resolvconf("/etc/resolv.conf")
# ctx.add_ta_file("root.key")
# ctx.add_ta_file("/etc/unbound/root.key")
ctx.set_option("auto-trust-anchor-file:", "root.key")


def is_ipaddr(x):
    try:
        ipaddr.IPAddress(x)
    except ValueError:
        return False
    return True


def check_ipv4(name):
    status, result = ctx.resolve(name, unbound.RR_TYPE_A, unbound.RR_CLASS_IN)
    return (name, ub_strerror(status), result.secure, result.data.address_list)


def check_ipv6(name):
    status, result = ctx.resolve(name, unbound.RR_TYPE_AAAA, unbound.RR_CLASS_IN)
    return (name, ub_strerror(status), result.secure, result.data.address_list)


def try_any(name):
    status, result = ctx.resolve(name, unbound.RR_TYPE_ANY, unbound.RR_CLASS_IN)
    return {"status": ub_strerror(status), "secure": result.secure}


from orm import session, HostName, Result

if __name__ == "__main__":

    for x in session.query(HostName):
        if not x.is_expired(NAME, age=60 * 60):
            continue
        hostname = x.get_hostname()
        if is_ipaddr(hostname):
            continue
        data = {}
        data.update(try_any(hostname))
        x.results.append(Result(NAME, data))
        pprint({hostname: data})
        session.commit()
