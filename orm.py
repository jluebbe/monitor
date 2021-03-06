#!/usr/bin/python

import collections
import json
import os.path
import operator
import hashlib
try:
    import urlparse
except ImportError:  # python 3
    import urllib.parse as urlparse

from datetime import datetime, timedelta

from pprint import pprint

from sqlalchemy import Table, Boolean, Column, DateTime, Integer, String, LargeBinary, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import ForeignKeyConstraint, Index, UniqueConstraint
from sqlalchemy.sql.expression import func
from sqlalchemy.types import TypeDecorator, VARCHAR
from sqlalchemy.orm.collections import attribute_mapped_collection, collection, MappedCollection
from sqlalchemy.ext.associationproxy import association_proxy

from sqlalchemy import event

# see /usr/share/doc/python-sqlalchemy-doc/examples/association/dict_of_sets_with_default.py


class JSONEncodedDict(TypeDecorator):

    "Represents an immutable structure as a json-encoded string."

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class MutationDict(Mutable, dict):

    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutationDict."

        if not isinstance(value, MutationDict):
            if isinstance(value, dict):
                return MutationDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()

MutationDict.associate_with(JSONEncodedDict)


class DefaultMappedCollection(MappedCollection):

    def __missing__(self, key):
        self[key] = x = Crawler(key)
        return x

path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'monitor.sqlite')
engine = create_engine('sqlite:///%s' % path, echo=True)


@event.listens_for(engine, "connect")
def on_connect(dbapi_con, con_record):
    cursor = dbapi_con.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

from sqlalchemy.orm import scoped_session, sessionmaker
session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()

links = Table('links', Base.metadata,
              Column('crawler_id', Integer, ForeignKey('crawlers.id'), index=True),
              Column('child_id', Integer, ForeignKey('nodes.id'), index=True),
              Index('ix_links_unique', 'crawler_id', 'child_id', unique=True),
              )


class Crawler(Base):
    __tablename__ = 'crawlers'
    query = session.query_property()

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('nodes.id'), index=True)
    method = Column(String(16), default='', index=True)

    def __init__(self, method):
        self.method = method

    def __repr__(self):
        return "<%s(%s on %r)>" % (self.__class__.__name__, self.method, self.parent)


class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        Index('ix_nodes_unique', 'type', 'name', unique=True),
    )
    __normalize_name__ = True
    query = session.query_property()

    id = Column(Integer, primary_key=True)
    type = Column(String(16), index=True)
    name = Column(String(), nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    conf = Column(JSONEncodedDict(), nullable=False, default={})
    __mapper_args__ = {'polymorphic_on': type}

    _child_crawlers = relationship("Crawler",
                                   backref=backref("parent", viewonly=True),
                                   collection_class=lambda: DefaultMappedCollection(operator.attrgetter('method')),
                                   cascade="all, delete, delete-orphan",
                                   )

    children = association_proxy(
        "_child_crawlers",
        "children",
    )

    parent_crawlers = relationship("Crawler",
                                   secondary=links,
                                   backref=backref("children"),
                                   )

    # is this really useful?
    parents = association_proxy(
        "parent_crawlers",
        "parent",
    )

    results = relationship("Result",
                           backref=backref('node'),
                           order_by="desc(Result.created)",
                           cascade="all, delete, delete-orphan",
                           lazy="dynamic",
                           )

    # make objects unique on name (in the scoped session)
    # see http://www.sqlalchemy.org/trac/wiki/UsageRecipes/UniqueObject
    @classmethod
    def __new__(cls, *args, **kwargs):
        # skip when loading
        if not 'name' in kwargs:
            return object.__new__(cls)
        name = cls.normalize(kwargs['name'])

        with session.no_autoflush:
            new = [x for x in session.new if type(x) == cls and x.name == name]
            if new:
                assert len(new) == 1
                return new[0]
            obj = Node.query.filter(
                (Node.type == cls.__mapper_args__['polymorphic_identity']) & (Node.name == name)
            ).first()
            if obj:
                return obj
            obj = object.__new__(cls)
            obj.__init__(name)
            session.add(obj)
        return obj

    @classmethod
    def normalize(cls, name):
        if not cls.__normalize_name__:
            return name
        url = urlparse.urlsplit(name)
        if not url.netloc:
            name = name.lower()
            if name[-1] == '.':
                return name[:-1]
            return name
        if url.hostname[-1] == '.':
            hostname = url.hostname[:-1]
        else:
            hostname = url.hostname
        if url.scheme == 'http':
            port = url.port or 80
        elif url.scheme == 'https':
            port = url.port or 443
        else:
            port = url.port
        if port:
            netloc = '%s:%i' % (hostname.lower(), port)
        else:
            netloc = '%s' % (hostname.lower(),)
        url = urlparse.urlunsplit((url.scheme, netloc, url.path, url.query, url.fragment))
        return url

    def __init__(self, name):
        self.name = self.__class__.normalize(name)
        self.conf = {}

    def __repr__(self):
        return "<%s(%r, %r, created=%s)>" % (self.__class__.__name__, self.id, self.name, self.created)

    def is_expired(self, method, age=300, retry=None):
        if retry is None:
            retry = age
        result = self.results.filter(Result.method == method).first()
        if not result:
            return True
        if (datetime.utcnow() - result.created) > timedelta(seconds=age):
            return True
        if not result.data and (datetime.utcnow() - result.created) > timedelta(seconds=retry):
            return True
        return False

    def get_hostname(self):
        url = urlparse.urlsplit(self.name)
        if not url.hostname:
            return self.name
        return url.hostname


class Entity(Node):
    __mapper_args__ = {'polymorphic_identity': 'entity'}
    __normalize_name__ = False


class HTTPService(Node):
    __mapper_args__ = {'polymorphic_identity': 'httpservice'}


class JSONAPI(HTTPService):
    __mapper_args__ = {'polymorphic_identity': 'jsonapi'}


class SpaceAPI(HTTPService):
    __mapper_args__ = {'polymorphic_identity': 'spaceapi'}


class Feed(HTTPService):
    __mapper_args__ = {'polymorphic_identity': 'feed'}


class HostName(Node):
    __mapper_args__ = {'polymorphic_identity': 'hostname'}


class DomainName(HostName):
    __mapper_args__ = {'polymorphic_identity': 'domainname'}


class MailServer(HostName):
    __mapper_args__ = {'polymorphic_identity': 'mailserver'}


class NameServer(HostName):
    __mapper_args__ = {'polymorphic_identity': 'nameserver'}


class XMPPServer(HostName):
    __mapper_args__ = {'polymorphic_identity': 'xmppserver'}


class IP4Address(Node):
    __mapper_args__ = {'polymorphic_identity': 'ip4address'}


class IP6Address(Node):
    __mapper_args__ = {'polymorphic_identity': 'ip6address'}


class EMailAddress(Node):
    __mapper_args__ = {'polymorphic_identity': 'emailaddress'}

    @classmethod
    def normalize(cls, name):
        if not '@' in name:
            raise ValueError("invalid email address '%s'" % name)
        url = urlparse.urlsplit(name)
        if not url.netloc:
            name = name.lower()
            if name[-1] == '.':
                return name[:-1]
            return "mailto:" + name
        if url.scheme and not url.scheme == "mailto":
            raise ValueError("invalid email address '%s'" % name)
        return name


class Result(Base):
    __tablename__ = "results"
    query = session.query_property()

    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey(Node.id), nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    method = Column(String(16), nullable=False)
    data = Column(JSONEncodedDict(), nullable=False, default={})

    __table_args__ = (
        Index("ix_results_node", "node_id", "method", "created"),
    )

    def __init__(self, method, data):
        self.method = method
        self.data = data

    def __repr__(self):
        return "<%s(%i, node=%i, %r, created=%s)>" % (self.__class__.__name__, self.id, self.node_id, self.method, self.created)


class SSLCert(Base):
    __tablename__ = "sslcerts"
    query = session.query_property()

    id = Column(Integer, primary_key=True)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_anchor = Column(Boolean, nullable=False)
    issuer_id = Column(Integer, ForeignKey('sslcerts.id'))
    subject = Column(String(), nullable=False)
    subject_der = Column(LargeBinary(), nullable=False, index=True)
    data_der = Column(LargeBinary(), nullable=False, unique=True, index=True)

    issuer = relationship("SSLCert", remote_side=[id])

    def data_hash(self):
        return "sha256/%s" % hashlib.sha256(self.data_der).hexdigest()

    def __repr__(self):
        return "<%s %i (%s, issuer=%r, created=%s)>" % (self.__class__.__name__, self.id, self.subject, self.issuer_id, self.created)


class SSLKey(Base):
    __tablename__ = "sslkeys"
    __table_args__ = (
        Index('ix_sslkeys_unique', 'key', 'cert_id', unique=True),
    )
    query = session.query_property()

    id = Column(Integer, primary_key=True)
    key = Column(String(), nullable=False, index=True)
    cert_id = Column(Integer, ForeignKey('sslcerts.id'))

    cert = relationship("SSLCert",
                        backref=backref('keys', cascade="all, delete-orphan"),
                        )

    def __init__(self, key):
        self.key = key

    def __repr__(self):
        return "<%s(key=%s, cert=%r)>" % (self.__class__.__name__, self.key, self.cert)

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    # Crawler.query.delete()
    # Node.query.delete()
    c = SpaceAPI(name="https://hickerspace.org").children["manual"]
    c.append(DomainName(name="hickerspace.org"))
    c.append(HTTPService(name="https://hickerspace.org"))
    HTTPService(name="http://totalueberwachung.de")
    c = SpaceAPI(name="https://stratum0.org").children["manual"]
    c.append(HTTPService(name="https://stratum0.org"))
    c.append(DomainName(name="stratum0.org"))
    c.append(DomainName(name="stratum0.net"))
    c.append(HostName(name="status.stratum0.org"))
    HTTPService(name="https://stratum0.net")
    HTTPService(name="https://ipv4.stratum0.net")
    HTTPService(name="https://ipv6.stratum0.net")
    directory = JSONAPI(name="http://spaceapi.net/directory.json")
    directory.conf = {"discover": "spaceapidirectory"}
    session.commit()
    print("Nodes:")
    pprint(session.query(Node).all())
    print("HTTPServices:")
    pprint(session.query(HTTPService).all())
