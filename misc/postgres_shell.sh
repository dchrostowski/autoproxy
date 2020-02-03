#!/bin/sh
echo default password is somepassword
docker exec -it autoproxy_db psql -U postgres proxies
