#!/bin/sh
docker-compose kill spider_scheduler
docker-compose rm --stop --force scrapyd
docker-compose stop
