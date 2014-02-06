#!/bin/bash
set -x
cd $(dirname $(readlink -fn -- "$0"))
./orm.py
./check_json.py
./discover_spaceapidirectory.py
./check_spaceapi.py
./discover_spaceapi.py
./check_host.py
./check_http.py
./discover_ips.py
./check_ip.py
./discover_dns.py
./check_services.py
./discover_services.py
./check_host.py
./discover_ips.py
./check_ip.py

