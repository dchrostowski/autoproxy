# -*- coding: utf-8 -*-

# Scrapy settings for autoproxy project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import logging

BOT_NAME = 'autoproxy'

SPIDER_MODULES = ['autoproxy.spiders']
NEWSPIDER_MODULE = 'autoproxy.spiders'

import os
import sys
CWD = os.path.dirname(os.path.realpath(__file__))
sys.path.append("%s/autoproxy/autoproxy_middleware" % CWD)



# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'autoproxy (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False
RETRY_ENABLED = False
DOWNLOAD_TIMEOUT =30
# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 16

# Configure a delay for requests for the same website (default: 0)gi
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 2
DOWNLOAD_DELAY_DEBUG = True
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 8
#CONCURRENT_REQUESTS_PER_IP = 100

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False
COOKIES_ENABLED = True


AUTOPROXY_RETRY = True
AUTOPROXY_RETRY_TIMES = 4

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'autoproxy.middlewares.AutoproxySpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'autoproxy.middlewares.AutoproxyDownloaderMiddleware': 543,
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None
    
}


RANDOM_UA_PER_PROXY = True
logging.getLogger('scrapy_user_agents.user_agent_picker').setLevel(logging.CRITICAL)


# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    'autoproxy.pipelines.AutoproxyPipeline': 300,
#}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
