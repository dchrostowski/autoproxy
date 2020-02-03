#!/bin/sh

docker-compose build scrapyd
docker-compose build spider_scheduler
docker-compose up -d scrapyd
docker-compose up -d spider_scheduler
docker-compose logs -f
