#!/bin/sh
docker-compose stop scrapyd
docker-compose rm -f autoproxy_scrapyd
docker-compose rm -f scrapyd

python3 misc/sync_to_db.py
docker-compose stop
