#!/usr/bin/python

import requests
import json
import urlparse

def fetch(url, timeout=10):
  assert(isinstance(url, basestring))
  url = urlparse.urlparse(url)
  page = requests.get(url.geturl(), timeout=timeout)
  try:
    return json.loads(page.content)
  except ValueError:
    return {}

from orm import session, JSONAPI, Result

import sqlalchemy

if __name__=="__main__":
    for x in session.query(JSONAPI):
        x.results.append(Result("jsonapi", fetch(x.name)))
        session.commit()

