#!/bin/sh

echo "waiting 30 seconds for scrapyd to be up..."
sleep 30
cd /code/autoproxy && scrapyd-client deploy $AUTOPROXY_ENV
python3 /scheduler/spider_scheduler.py