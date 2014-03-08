#!/usr/bin/python

NAME = "spaceapi"

import requests
import json
import urlparse
from bs4 import BeautifulSoup

def pretty_json(data):
  return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))

def fetch(url, timeout=10):
  assert(isinstance(url, basestring))
  baseurl = url = urlparse.urlparse(url)
  try:
    page = requests.get(url.geturl(), timeout=timeout)
  except requests.exceptions.SSLError as e:
    print e
    return {}
  except requests.exceptions.Timeout as e:
    print e
    return {}
  except requests.exceptions.ConnectionError:
    return {}
  try:
    return json.loads(page.content)
  except ValueError:
    pass
  if 'text/html' in page.headers['content-type']:
    dom = BeautifulSoup(page.text)
    meta = dom.find("link", rel="space-api")
    if meta:
      url = urlparse.urlparse(meta['href'])
      if url.scheme == "":
        url = urlparse.urlparse("%s://%s%s"%(baseurl.scheme, baseurl.netloc, meta['href']))
      return fetch(url.geturl())

#print pretty_json(fetch("https://hickerspace.org"))
#print pretty_json(fetch("https://stratum0.org"))

from orm import session, SpaceAPI, Result

for x in session.query(SpaceAPI):
    if not x.is_expired(NAME):
        continue
    x.results.append(Result(NAME, fetch(x.name)))
    session.commit()

