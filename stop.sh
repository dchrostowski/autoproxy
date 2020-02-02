#!/bin/sh
docker-compose stop scrapyd
docker-compose rm -f autoproxy_scrapyd
docker-compose rm -f scrapyd
docker-compose stop
