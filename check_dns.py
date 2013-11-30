#!/usr/bin/python

from unbound import ub_ctx,RR_TYPE_A,RR_CLASS_IN

ctx = ub_ctx()
#ctx.resolvconf("/etc/resolv.conf")
#ctx.add_ta_file("root.key")
#ctx.add_ta_file("/etc/unbound/root.key")
ctx.set_option("auto-trust-anchor-file:", "root.key")

status, result = ctx.resolve("stratum0.net", RR_TYPE_A, RR_CLASS_IN)
print status, result.secure

