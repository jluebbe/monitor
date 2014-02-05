#!/usr/bin/python

import sys
import logging

import orm

from flask import flash, render_template, jsonify
from flask import Flask, Markup, Response

app = Flask("monitor")
app.config.from_pyfile("webif.conf")

@app.teardown_appcontext
def shutdown_session(exception=None):
    orm.session.remove()

@app.template_filter('link')
def link_filter(x):
    url = None
    if isinstance(x, orm.Node):
        url = u'/node/%i' % (x.id,)
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
    return render_template("node.html",
                           node=node,
                           results=node.results.all(),
                           parents=node.parents,
                           children=node.children)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    app.run(port=9090, debug=True)

