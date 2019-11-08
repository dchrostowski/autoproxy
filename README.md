# autoproxy

This is a rewrite of my public proxy farm.  It uses redis to record and store reliability statistics for publicly available proxy servers.

After recording sufficient data, it is able to create a database of proxy servers and choose the most reliable proxy to use for crawling a given website.
