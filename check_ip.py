#!/usr/bin/python

NAME = "whois"

from ipaddr import IPAddress
from pprint import pprint
import subprocess

CMD = "\
whois\
 -h whois.ripe.net\
 -s RIPE-GRS,AFRINIC-GRS,APNIC-GRS,ARIN-GRS,JPIRR-GRS,LACNIC-GRS,RADB-GRS\
 -r\
 -T route,inetnum,inet6num\
".split()


def parse(rpsl):
    result = []
    state = {}
    key, value = '', ''
    for line in rpsl:
        if not line or line[0] == '%':
            if state:
                result.append(state)
            state = {}
            continue
        print(line)
        if state and key == 'descr' and line[0] == ' ':
            state['descr'].append(line.strip())
            continue
        if line[0] == ' ':
            continue
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()
        if not state and key in ['route', 'inetnum', 'inet6num']:
            state['type'] = key
            state['key'] = value
        if state and key in ['source', 'netname']:
            state[key] = value
        if state and key == 'descr':
            state.setdefault('descr', []).append(value)
    return result


def query(address):
    address = IPAddress(address)
    print(address)
    p = subprocess.Popen(CMD + [str(address)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = p.communicate()[0]
    print(result)
    result = result.decode('ISO-8859-1').strip()
    if p.returncode != 0:
        print(result)
        raise Exception("whois failed with %i" % p.returncode)
    result = result.split('\n')
    return result

from orm import session, Node, Result

if __name__ == "__main__":
    for x in session.query(Node).filter((Node.type == "ip4address") | (Node.type == "ip6address")).all():
        if not x.is_expired(NAME, age=24 * 60 * 60):
            continue
        pprint(x)
        address = x.name
        data = {}
        data["raw"] = query(address)
        data["parsed"] = parse(data["raw"])
        pprint(data)
        x.results.append(Result(NAME, data))
        session.commit()
