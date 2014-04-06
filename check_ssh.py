#!/usr/bin/python

NAME = "ssh"

import socket
import paramiko


def fetch(host, port):
    result = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except socket.gaierror:
        return {}
    except socket.error:
        return {}
    try:
        t = paramiko.Transport(s)
        t.start_client()
    except paramiko.SSHException:
        return {}
    k = t.get_remote_server_key()
    # TODO: get DSA key as well
    if isinstance(k, paramiko.RSAKey):
        result["rsa-pkey"] = k.get_base64()
        result["rsa-bits"] = k.get_bits()
    return result

from orm import session, HostName, Result

if __name__ == "__main__":
    for x in session.query(HostName):
        if not x.is_expired(NAME, age=7 * 24 * 60 * 60, retry=60 * 60):
            continue
        hostname = x.get_hostname()
        x.results.append(Result(NAME, fetch(hostname, 22)))
        session.commit()
