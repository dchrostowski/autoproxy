#!/bin/sh

curl http://localhost:6800/schedule.json -d project=autoproxy -d spider=$1
curl http://localhost:6800/listjobs.json?project=autoproxy