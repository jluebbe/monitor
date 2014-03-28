#!/usr/bin/python

NAME = "ssl"

import json
import urlparse
import socket
from OpenSSL import SSL

from ssl_ca import add_cert

def fetch(host, port, timeout=10):
  context = SSL.Context(SSL.TLSv1_METHOD)
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  connection = SSL.Connection(context, s)
  connection.set_tlsext_host_name(host)
  connection.connect((host, port))
  connection.setblocking(1)
  try:
    connection.do_handshake()
  except OpenSSL.SSL.WantReadError:
    connection.close()
    return {}
  chain = []
  for cert in connection.get_peer_cert_chain():
    c = add_cert(cert)
    chain.append((c.subject, c.data_hash()))
  return {'chain': chain}

from orm import session, HTTPService, Result

if __name__=="__main__":
    for x in HTTPService.query:
        print x.name
        if not x.is_expired(NAME):
            continue
        url = urlparse.urlparse(x.name)
        if url.scheme == 'https':
          x.results.append(Result(NAME, fetch(url.hostname, url.port or 443)))
        else:
          continue
        session.commit()

