#!/bin/sh
chmod +x /start/scrapyd.env
htpasswd -b -c /etc/nginx/htpasswd $SCRAPYD_USERNAME $SCRAPYD_PASSWORD
service nginx start
/usr/local/bin/scrapyd