#!/usr/bin/python

import urlparse
import yaml

with open("entities.yaml") as f:
  data = yaml.load(f)

#print yaml.dump(data, default_flow_style = False, default_style='"')
#print yaml.dump(data, default_flow_style = False)
print repr(data)

from orm import session, Node, Entity, Result

owners = {}
users = {}
for entity, categories in data.items():
  for category, names in categories.items():
    for name in names:
      if category.lower() == 'owner':
        assert not name in owners
        owners[name] = Entity(name=entity)
      elif category.lower() == 'user':
        users.setdefault(name, []).append(Entity(name=entity))

# create new entity nodes
#session.commit()

names = {}
for x in Node.query:
  url = urlparse.urlparse(x.name)
  if url.hostname:
    names.setdefault(url.hostname, []).append(x)
  else:
    names.setdefault(x.name, []).append(x)

for x in Entity.query:
  c = x.children["owner"]
  while c:
    c.pop()
  c = x.children["user"]
  while c:
    c.pop()
  if not x.name in data:
    session.delete(x)

for name, entity in owners.items():
  nodes = names.get(name, [])
  if nodes:
    c = entity.children["owner"]
    for node in nodes:
      c.append(node)
  else:
    print "Node for '%s' not found" % name

for name, entities in users.items():
  nodes = names.get(name, [])
  if nodes:
    for entity in entities:
      c = entity.children["user"]
      for node in nodes:
        c.append(node)
  else:
    print "Node for '%s' not found" % name

session.commit()

