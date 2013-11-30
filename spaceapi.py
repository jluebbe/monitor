#!/usr/bin/python

import requests
import json
import urlparse
from bs4 import BeautifulSoup

def pretty_json(data):
  return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))

def fetch(url, timeout=10):
  assert(isinstance(url, basestring))
  baseurl = url = urlparse.urlparse(url)
  page = requests.get(url.geturl(), timeout=timeout)
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
        url = urlparse.urlparse("%s://%s%s"%(baeurl.scheme, baseurl.netloc, meta['href']))
      return fetch(url.geturl())

print pretty_json(fetch("https://hickerspace.org"))
print pretty_json(fetch("https://stratum0.org"))

