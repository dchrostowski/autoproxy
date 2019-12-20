# autoproxy


### About

This is a rewrite of my public proxy farm.  It uses redis to record and store reliability statistics for publicly available proxy servers.

After recording sufficient data, it is able to create a database of proxy servers and choose the most reliable proxy to use for crawling a given website.

### Pre-requisites
* docker
* docker-compose

### Overview
When web crawling, proxies are essential for maintaining anonymity and circumventing bot detection.  There are a number of free public proxy servers spread across the Internet, however their performance is inconsistent.  For example, a particular proxy may work for one site but not another when web crawling. This project aims to create a proxy farm that stores performance and reliability statistics for public proxies on a per-site basis.

This project utilizes a redis store to temporarily store and cache proxy server information for use by a scrapy middleware.  This cache is then periodically synced to a Postgres database intended to be a more permanent and practical storage medium for proxy statistics.  After syncing, the redis store is flushed and new proxy servers from the database are rotated into the cache for use again.

### Example Usage

I'm still working on this, but here's how to run it:

```
git clone https://github.com/dchrostowski/autoproxy.git
cd autoproxy
docker-compose build
docker-compose up
```
To schedule jobs and such, there is a scrapyd service running.  Open a browser and go to `http://localhost:6800`.  More information on scrapyd is available at `https://scrapyd.readthedocs.io/en/latest/`.

### Conceptual Model
This system incorporates an object-oriented design approach to catalog proxies.  The three critical classes are `Proxy`, `Queue`, and `Detail`.  The `Proxy` class simply contains a static representation of an IP address, port, and protocol of a public proxy server.  The `Queue` class is used to represent a target web resource to scrape.  The `Detail` class contains proxy data which is continually updated for a given `Proxy` and `Queue`.  The purpose for each of these classes are documented in detail below.

#### Proxy
A `Proxy` object has the following fields:
* `address` - The IP address of a proxy server
* `port` - The TCP port of the proxy server
* `protocol` - The protocol of the proxy server (SOCKS4, SOCKS5, http, etc.)
* `proxy_id` - An ID to be referenced by a `Detail` object as a foreign key (this is generated automatically)
##### Example
```
proxy = Proxy(address='1.2.3.4', port=8080, protocol='https')
```

#### Queue
A `Queue` obect has the following fields:
* `domain` - the domain of the target resource (e.g. google.com)
* `queue_id` - An ID to be referenced by a `Detail` object as a foreign key

A new `Queue` is automatically generated when the `ProxyManager` encounters a domain that has not been scraped yet.  There are two special reserved queues: a **seed queue** and an **aggregate queue**.

The **seed queue** keeps statisitcs for a designated endpoint which does not not block or otherwise refuse HTTP connections.  This essentially provides a control to test if a given proxy actually works or not.  Other `Queues` will populate themselves over time by cloning `Details` out of the **seed queue** and testing them against their designated targets.  When a new `Proxy` object is created, a `Detail` will be generated and inserted into the **seed queue**.

The **aggregate queue** simply keeps aggregated statistics of all `Queues` using a given `Proxy`.

##### Example
```
queue = Queue(domain='google.com')
```

#### Detail
A `Detail` object has the following fields:
* `proxy_id` - The ID of a `Proxy` object (basically the address, port, and protocol of the proxy server)
* `queue_id` - The ID of the `Queue` object this `Detail` is recording statistics for (basically the target website ID)
* `active` - a boolean that is set to `True` upon a successful response during a crawl.
* `load_time` - How many milliseconds it took to get a response on the last request.
* `last_used` - A timestamp of when this proxy server was used.
* `last_active` - A timestap of when this proxy server was last successfully used.
* `bad_count` - A counter of how many bad responses have occurred recently.  When `bad_count` passes a predefined threshold, it will be reset to 0 and then set `blacklisted` to `True`.
* `blacklisted` - A boolean which when set to True indicates not to use the referenced proxy server.
* `blacklisted_count` - A count of how many times `blacklisted` has been set to `True`.
* `lifetime_good` - Lifetime number of successful crawls with the referenced proxy server.
* `lifetime_bad` - Lifetime number of unsuccessful crawls with the referenced proxy server.
##### Example
```
# Create a new detail for a given proxy and site
detail = Detail(proxy_id=1,queue_id=2)
```
### Other classes
#### ProxyObject
To do
#### StorageManager
To do
#### PostgresManager
To do
#### RedisManager
To do
#### ProxyManager
to do

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




