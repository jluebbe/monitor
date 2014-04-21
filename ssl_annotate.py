#!/usr/bin/python

from pprint import pprint

from orm import engine, session, Result, SSLCert, SSLKey


def annotate(result):
    if not result.data:
        return
    if "resolved" in result.data:
        return
    digest = result.data["chain"][0][1]
    key = session.query(SSLKey).filter(SSLKey.key == digest).first()
    if key is None:
        print "Missing key for digest %s" % digest
        return
    cert = key.cert
    pprint(result.data)
    pprint(key)
    resolved = []
    while cert:
        resolved.append((cert.subject, cert.data_hash()))
        if cert == cert.issuer:
            break
        cert = cert.issuer
    result.data["resolved"] = resolved

if __name__ == "__main__":
    # engine.echo = False
    # for result in session.query(Result).filter(Result.method == 'ssl').group_by(Result.node_id).order_by(Result.created.desc()):
    for result in session.query(Result).filter(Result.method == 'ssl').order_by(Result.created.desc()):
        annotate(result)
    session.commit()
