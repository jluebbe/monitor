#!/bin/bash
set -ex
cd $(dirname $(readlink -fn -- "$0"))
rm monitor.sql*
./orm.py

