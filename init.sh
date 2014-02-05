#!/bin/bash
set -x
cd $(dirname $(readlink -fn -- "$0"))
rm monitor.sql*
./orm.py

