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
Open a browser and go to `http://localhost:5000/runspider`

This will run a spider against my proxy tester API and print out the results on the page.




