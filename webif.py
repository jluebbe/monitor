#!/usr/bin/python

import sys
import logging
import os.path

import orm

from flask import flash, render_template, jsonify
from flask import Flask, Markup, Response

this = os.path.dirname(os.path.abspath(__file__))

app = Flask("monitor")
app.config.from_pyfile(os.path.join(this), "webif.conf")


@app.teardown_appcontext
def shutdown_session(exception=None):
    orm.session.remove()


@app.template_filter('link')
def link_filter(x):
    url = None
    if isinstance(x, orm.Node):
        url = u'/node/%i' % (x.id,)
    if isinstance(x, orm.Crawler):
        url = u'/node/%i' % (x.parent_id,)
    if url:
        return Markup('<a href="%s">%r</a>') % (url, x)
    else:
        return u'%r' % (x,)


@app.route('/')
def index():
    return render_template("index.html", nodes=orm.Node.query.all())


@app.route('/node/<int:id>')
def node(id):
    node = orm.Node.query.filter(orm.Node.id == id).first()
    # move this to a read-only property on Node?
    method_parents = {}
    for crawler in node.parent_crawlers:
        method_parents.setdefault(crawler.method, []).append(crawler.parent)
    peers = orm.Node.query.filter(orm.Node.name == node.name, orm.Node.id != node.id).all()
    return render_template("node.html",
                           node=node,
                           results=node.results.all(),
                           method_parents=method_parents,
                           children=node.children,
                           peers=peers,
                           )

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    app.run(port=9090, debug=True)
