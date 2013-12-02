#!/usr/bin/python

import collections
import json
import os.path

from pprint import pprint

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.expression import func
from sqlalchemy.types import TypeDecorator, VARCHAR

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

Base = declarative_base()

class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True)
    type = Column(String(16), index=True)
    parent_id = Column(Integer, ForeignKey('nodes.id'))
    created = Column(DateTime, nullable=False, default=func.now())
    # FIXME: if the check results in an unchanged Node, updated is not changed
    updated = Column(DateTime, nullable=False, index=True, default=func.now(), onupdate=func.now())
    name = Column(String(), nullable=False)
    conf = Column(JSONEncodedDict(), nullable=False, default={})
    data = Column(JSONEncodedDict(), nullable=False, default={})
    __mapper_args__ = {'polymorphic_on': type}

    children = relationship("Node",
        backref=backref('parent', remote_side=[id]),
        cascade="all, delete, delete-orphan",
    )

    def __repr__(self):
        return "<%s(%s, %r, created=%s, updated=%s)>" % (self.__class__.__name__, self.id, self.name, self.created, self.updated)

class SpaceAPI(Node):
    __mapper_args__ = {'polymorphic_identity': 'spaceapi'}

class HTTPService(Node):
    __mapper_args__ = {'polymorphic_identity': 'httpservice'}

class HostName(Node):
    __mapper_args__ = {'polymorphic_identity': 'hostname'}

class DomainName(HostName):
    __mapper_args__ = {'polymorphic_identity': 'domainname'}

path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'monitor.sqlite')
engine = create_engine('sqlite:///%s' % path, echo=True)
Base.metadata.create_all(engine)

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
session = Session()

if __name__=="__main__":
    session.query(Node).delete()
    hickerspace = SpaceAPI(name="https://hickerspace.org")
    hickerspace.children.append(HTTPService(name="https://hickerspace.org"))
    hickerspace.children.append(DomainName(name="hickerspace.org"))
    session.add(hickerspace)
    session.add(HTTPService(name="http://totalueberwachung.de"))
    stratum0 = SpaceAPI(name="https://stratum0.org")
    stratum0.children.append(HTTPService(name="https://stratum0.org"))
    stratum0.children.append(DomainName(name="stratum0.org"))
    stratum0.children.append(DomainName(name="stratum0.net"))
    stratum0.children.append(HostName(name="status.stratum0.org"))
    session.add(stratum0)
    session.commit()
    print "Nodes:"
    pprint(session.query(Node).all())
    print "HTTPServices:"
    pprint(session.query(HTTPService).all())

