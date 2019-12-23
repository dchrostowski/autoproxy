#!/bin/sh

cd /code/autoproxy && scrapyd-client deploy scrapyd
python3 /scheduler/spider_scheduler.py