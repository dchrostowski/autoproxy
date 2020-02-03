#!/bin/sh

cd /code/autoproxy && scrapyd-client deploy $AUTOPROXY_ENV
python3 /scheduler/spider_scheduler.py