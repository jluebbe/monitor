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
  page = requests.get(url.geturl(), timeout=timeout, allow_redirects=False)
  page.headers['status'] =  page.status_code
  return dict(page.headers)

print fetch("http://totalueberwachung.de")
print fetch("https://stratum0.org")

