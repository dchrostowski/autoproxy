#!/bin/sh
echo $USERNAME
htpasswd -b -c /etc/nginx/htpasswd $USERNAME $PASSWORD
service nginx start
/usr/local/bin/scrapyd