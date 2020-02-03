#!/bin/sh
python3 create_htpasswd.py
service nginx start
/usr/local/bin/scrapyd