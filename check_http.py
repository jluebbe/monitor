#!/usr/bin/python

NAME = "httpservice"

import requests
import json
import urlparse
from bs4 import BeautifulSoup


def pretty_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))


def fetch(url, timeout=10):
    assert(isinstance(url, basestring))
    url = urlparse.urlparse(url)
    if not url.scheme in ['http', 'https']:
        return {}
    try:
        page = requests.get(url.geturl(), timeout=timeout, allow_redirects=False)
        page.headers['status'] = page.status_code
        return dict(page.headers)
    except requests.exceptions.SSLError as e:
        print e
        return {}
    except requests.exceptions.Timeout as e:
        print e
        return {}
    except requests.exceptions.ConnectionError as e:
        print e
        return {}
    except requests.exceptions.MissingSchema:
        return fetch("http://" + url.geturl(), timeout)

# print fetch("http://totalueberwachung.de")
# print fetch("https://stratum0.org")

from orm import session, HTTPService, Result

if __name__ == "__main__":
    for x in HTTPService.query:
        print x.name
        if not x.is_expired(NAME):
            continue
        x.results.append(Result(NAME, fetch(x.name)))
        session.commit()
