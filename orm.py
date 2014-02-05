#!/usr/bin/python

import collections
import json
import os.path

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

from sqlalchemy import event

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

class Link(Base):
    __tablename__ = 'links'
    query = session.query_property()

    parent_id = Column(Integer, ForeignKey('nodes.id'), primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey('nodes.id'), primary_key=True, index=True)

class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        Index('ix_nodes_unique', 'type', 'name', unique=True),
    )
    query = session.query_property()

    id = Column(Integer, primary_key=True)
    type = Column(String(16), index=True)
    name = Column(String(), nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    conf = Column(JSONEncodedDict(), nullable=False, default={})
    __mapper_args__ = {'polymorphic_on': type}

    children = relationship("Node",
        secondary="links",
        primaryjoin=id==Link.parent_id,
        secondaryjoin=id==Link.child_id,
        backref=backref("parents")
    )

    results = relationship("Result",
        backref=backref('node'),
        order_by="desc(Result.created)",
        cascade="all, delete, delete-orphan",
        lazy="dynamic",
    )

    # make objects unique on name (in the scoped session)
    @classmethod
    def __new__(cls, bases, name=None):
        # skip when loading
        if name is None:
            return object.__new__(cls, bases)

        with session.no_autoflush:
            obj = cls.query.filter(Node.name == name).first()
            if not obj:
                obj = object.__new__(cls, bases)
                obj.__init__(name)
                session.add(obj)
        return obj

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<%s(%r, %r, created=%s)>" % (self.__class__.__name__, self.id, self.name, self.created)

    def is_expired(self, method, age=300):
        limit = datetime.utcnow()-timedelta(seconds=age)
        result = self.results.filter(Result.method==method).first()
        if not result:
            return True
        if not result.data:
            return True
        return result.created < limit

class HTTPService(Node):
    __mapper_args__ = {'polymorphic_identity': 'httpservice'}

class JSONAPI(HTTPService):
    __mapper_args__ = {'polymorphic_identity': 'jsonapi'}

class SpaceAPI(HTTPService):
    __mapper_args__ = {'polymorphic_identity': 'spaceapi'}

class HostName(Node):
    __mapper_args__ = {'polymorphic_identity': 'hostname'}

class DomainName(HostName):
    __mapper_args__ = {'polymorphic_identity': 'domainname'}

class IP4Address(Node):
    __mapper_args__ = {'polymorphic_identity': 'ip4address'}

class IP6Address(Node):
    __mapper_args__ = {'polymorphic_identity': 'ip6address'}

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

    def __repr__(self):
        return "<%s %i (%s, issuer=%r, created=%s)>" % (self.__class__.__name__, self.id, self.subject, self.issuer_id, self.created)

Base.metadata.create_all(engine)
session.remove()

if __name__=="__main__":
    Link.query.delete()
    Node.query.delete()
    hickerspace = SpaceAPI(name="https://hickerspace.org")
    hickerspace.children.append(DomainName(name="hickerspace.org"))
    hickerspace.children.append(HTTPService(name="https://hickerspace.org"))
    HTTPService(name="http://totalueberwachung.de")
    stratum0 = SpaceAPI(name="https://stratum0.org")
    stratum0.children.append(HTTPService(name="https://stratum0.org"))
    stratum0.children.append(DomainName(name="stratum0.org"))
    stratum0.children.append(DomainName(name="stratum0.net"))
    stratum0.children.append(HostName(name="status.stratum0.org"))
    directory = JSONAPI(name="http://spaceapi.net/directory.json")
    directory.conf = {"discover": "spaceapidirectory"}
    session.commit()
    print("Nodes:")
    pprint(session.query(Node).all())
    print("HTTPServices:")
    pprint(session.query(HTTPService).all())

