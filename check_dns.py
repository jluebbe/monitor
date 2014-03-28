#!/usr/bin/python

from unbound import ub_ctx, ub_strerror, RR_TYPE_A, RR_TYPE_AAAA, RR_TYPE_CNAME, RR_CLASS_IN

ctx = ub_ctx()
# ctx.resolvconf("/etc/resolv.conf")
# ctx.add_ta_file("root.key")
# ctx.add_ta_file("/etc/unbound/root.key")
ctx.set_option("auto-trust-anchor-file:", "root.key")


def check_ipv4(name):
    status, result = ctx.resolve(name, RR_TYPE_A, RR_CLASS_IN)
    return (name, ub_strerror(status), result.secure, result.data.address_list)


def check_ipv6(name):
    status, result = ctx.resolve(name, RR_TYPE_AAAA, RR_CLASS_IN)
    return (name, ub_strerror(status), result.secure, result.data.address_list)

if __name__ == "__main__":
    print check_ipv4("stratum0.net")
    print check_ipv6("stratum0.net")
    print check_ipv4("stratum0.org")
    print check_ipv4("dnssec.nl")
    print check_ipv4("google.de")
    print check_ipv6("google.de")
