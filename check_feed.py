#!/usr/bin/python

NAME = "feed"

import requests
import json
import urlparse
import feedparser
import icalendar
import pytz

from dateutil.rrule import rrulestr
from dateutil.relativedelta import relativedelta
from datetime import date, datetime


def pretty_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))


def fetch_ical(url, timeout=10):
    result = {'ical': {}}
    assert(isinstance(url, basestring))
    url = urlparse.urlparse(url)
    if not url.scheme in ['http', 'https']:
        return {}
    try:
        page = requests.get(url.geturl(), timeout=timeout)
    except requests.exceptions.SSLError as e:
        print e
        return {'error': 'ssl'}
    except requests.exceptions.Timeout as e:
        print e
        return {'error': 'timeout'}
    except requests.exceptions.ConnectionError:
        return {'error': 'connection'}
    try:
        cal = icalendar.Calendar.from_ical(page.content)
        count = 0
        summaries = []
        print cal
        for event in cal.walk('VEVENT'):
            print event
            if 'CANCELLED' in event:
                continue
            dts = event['DTSTART'].dt
            tz = getattr(dts, 'tzinfo', None)
            s = datetime.now(tz) + relativedelta(months=-1)
            e = datetime.now(tz) + relativedelta(months=0)
            if 'RRULE' in event:
                rr = rrulestr(event['RRULE'].to_ical(), dtstart=dts)
                recent = rr.between(s, e)
                print recent
                summary = event.get('SUMMARY', 'n/a')
                for r in recent:
                    count += 1
                    summary += " " + r.isoformat()
                if recent:
                    summaries.append(summary)
                continue
            elif type(dts) == datetime and s <= dts <= e:
                print dts
            elif type(dts) == date and s.date() <= dts <= e.date():
                print dts
            else:
                continue
            count += 1
            summaries.append(event.get('SUMMARY', 'n/a') + " " + dts.isoformat())
        result['ical']['count'] = count
        result['ical']['recent'] = summaries
    except ValueError as e:
        return {'error': 'parsing'}
    return result


def fetch_feed(url, timeout=10):
    result = {'feed': {}}
    assert(isinstance(url, basestring))
    url = urlparse.urlparse(url)
    if not url.scheme in ['http', 'https']:
        return {}
    try:
        d = feedparser.parse(url.geturl())
        result['content-type'] = d.headers['content-type']
        result['feed']['count'] = len(d.entries)
    except Exception as e:
        print e
        return {}
    return result

# print fetch("http://totalueberwachung.de")
# print fetch("https://stratum0.org")

from orm import session, Feed, Result

if __name__ == "__main__":
    for x in Feed.query:
        print x.name
        # if not x.is_expired(NAME):
        #    continue
        print x.conf
        if x.conf['kind'] in ['calendar', 'events']:
            x.results.append(Result(NAME, fetch_ical(x.name)))
        else:
            continue
            x.results.append(Result(NAME, fetch_feed(x.name)))
        session.commit()
