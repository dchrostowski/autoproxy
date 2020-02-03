# autoproxy


### About

This is a rewrite of my public proxy farm.  It uses redis to record and store reliability statistics for publicly available proxy servers.

After recording sufficient data, it is able to create a database of proxy servers and choose the most reliable proxy to use for crawling a given website.

### Pre-requisites
* docker
* docker-compose

### Overview
When web crawling, proxies are essential for maintaining anonymity and circumventing bot detection.  There are a number of free public proxy servers spread across the Internet, however their performance is inconsistent. This project utilizes a redis store to temporarily store and cache proxy server information for use by a scrapy middleware.  This cache is then periodically synced to a Postgres database intended to be a more permanent and practical storage medium for proxy statistics. 

### Example Usage

I'm still working on this, but here's how to run it:

```
git clone https://github.com/dchrostowski/autoproxy.git
cd autoproxy
docker-compose build
docker-compose up
```

### Getting proxies

There are a few spiders (see autoproxy/autoproxy/spiders) that are scheduled to crawl a few sites to constantly pull in more proxies and then test those proxies against the sites they've scraped.

To access the Postgres database, you can run the following:
```
docker exec -it autoproxy_db psql -U postgres proxies
```
The default password is `somepassword`

### Future plans

I'm planning on publishing the autoproxy_package/ contents as a module/package eventually.