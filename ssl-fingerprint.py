#!/usr/bin/python3


import socket, ssl, pprint, hashlib

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('www.google.com', 443))
# require a certificate from the server
ssl_sock = ssl.wrap_socket(s)
#                           ca_certs="/etc/ca_certs_file",
#                           cert_reqs=ssl.CERT_REQUIRED)

cert = ssl_sock.getpeercert(True)
print(cert)
print("md5", hashlib.md5(cert).hexdigest())
print("sha1", hashlib.sha1(cert).hexdigest())
pprint.pprint(ssl_sock.getpeercert())
pprint.pprint(ssl_sock.cipher())
# note that closing the SSLSocket will also close the underlying socket
ssl_sock.close()  
