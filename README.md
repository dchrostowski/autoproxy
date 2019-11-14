# autoproxy


### About

This is a rewrite of my public proxy farm.  It uses redis to record and store reliability statistics for publicly available proxy servers.

After recording sufficient data, it is able to create a database of proxy servers and choose the most reliable proxy to use for crawling a given website.

### Pre-requisites
* docker
* docker-compose

### Example Usage

I'm still working on this, but here's how to run it:

```
git clone https://github.com/dchrostowski/autoproxy.git
cd autoproxy
docker-compose build
docker-compose up
```
Open a browser and go to `http://localhost:5000/runspider?spider=gatherproxy&count=1`

This will run a spider against my proxy tester API and print out the results on the page.

### Database

To manually sync the redis cache with the database there are two options:
#### Option 1
Open a browser and go to `http://localhost:5000/sync_to_db`

#### Option 2
Invoke the `sync_to_db()` method in the StorageManager class.  Below is a simple example:
1. Get a bash shell inside the web docker container and open the Python interpretter:
```
docker exec -it autoproxy3_web_1 /bin/bash
python3
```
2. In the python interpretter type the following:
```
from storage_manager import StorageManager
storage_mgr = StorageManager()
storage_mgr.sync_to_db()
```
This will insert/update any new proxies/statistics and then flush the redis cache.




