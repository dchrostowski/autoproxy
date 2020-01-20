#!/bin/sh
docker-compose rm --stop --force scrapyd
docker-compose kill spider_scheduler
docker-compose stop
