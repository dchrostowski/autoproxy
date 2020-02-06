# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy.exceptions import IgnoreRequest
from scrapy import signals

from scrapy_autoproxy.proxy_manager import ProxyManager
from scrapy_autoproxy.exception_manager import ExceptionManager
from scrapy_autoproxy.util import parse_domain
from scrapy_autoproxy.storage_manager import RedisDetailQueueEmpty
import sys
import logging
import twisted
import time
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


class AutoproxySpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request, dict
        # or Item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)




class AutoproxyDownloaderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    def __init__(self,crawler):
        self.retry = crawler.settings.getbool('AUTOPROXY_RETRY',True)
        self.retry_times = crawler.settings.getint('AUTOPROXY_RETRY_TIMES', 2)
        default_neutral = crawler.settings.get('RETRY_HTTP_CODES',[]) + [404]
        self.neutral_codes = crawler.settings.get('NEUTRAL_HTTP_CODES', default_neutral)
        self.bad_codes = crawler.settings.get('BAD_HTTP_CODES',[400,401,402,403])
        self.good_codes = crawler.settings.get('GOOD_HTTP_CODES', [200])
        

        self.proxy_mgr = ProxyManager()
        
        
        
        

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls(crawler)
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.
        
        spider.logger.info("processing request for %s" % request.url)
        if parse_domain(request.url) not in spider.allowed_domains:
            raise IgnoreRequest("Bad domain, ignoring request.")
        
        proxy = self.proxy_mgr.get_proxy(request.url)
        logger.info("using proxy %s" % proxy.urlify())
        request.meta['proxy'] = proxy.urlify()
        request.meta['proxy_obj'] = proxy

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest


        ## to do, use request.meta['download_latency']
        spider.logger.info("processing response for %s" % request.url)
        proxy = request.meta.get('proxy_obj',None)

        

        
        if proxy:

            if parse_domain(request.url) not in spider.allowed_domains and parse_domain(response.url) not in spider.allowed_domains:
                logger.info("proxy redirected to a bad domain, marking bad")
                proxy.callback(success=False)
                return response

            
            
            if response.status in self.good_codes:
                logging.info("Got an explicitly good response code, marking good")
                proxy.callback(success=True)
            
            elif response.status in self.neutral_codes:
                logging.info("Got an explicitly neutral response, marking success=None")
                proxy.callback(success=None)

            elif response.status in self.bad_codes:
                logging.info("Got an explcitly bad response code, marking bad")
                proxy.callback(success=False)

            elif response.status >= 400:
                logging.info("status code > 399, marking bad")
                proxy.callback(success=False)
            
            elif response.status < 400:
                logging.info("Got a status code < 400, marking good")
                proxy.callback(success=True)
            

            else:
                logging.warn("Got a weird edge case for an HTTP status code")
                proxy.callback(success=None)

            
            
        
        return response

    def process_exception(self, request, exception, spider):
        
        # Called when a download handler or a process_request()F
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        spider.logger.info("processing exception for %s" % request.url)
        proxy = request.meta.get('proxy_obj',None)
        
        if proxy is not None:
            if type(exception) is twisted.internet.error.TimeoutError:
                proxy.callback(success=False)
                logger.error("Request tmed out with proxy %s." % proxy.urlify())
                if self.retry:
                    retried = request.meta.get('autoproxy_tries',0) + 1
                    
                    if retried > self.retry_times:
                        logging.error("url %s has exceeded max autoproxy retry attempts.  giving up..." % request.url)
                        return None
                    else:
                        new_proxy = self.proxy_mgr.get_proxy(request.url)
                        request.meta['proxy_obj'] = new_proxy
                        request.meta['proxy'] = new_proxy.urlify()
                        request.meta['autoproxy_tries'] = retried
                        logging.error("Retrying request with a new proxy.")
                        return request
            

        if type(exception) == RedisDetailQueueEmpty:
            return None

        if proxy is None:
            logger.warn("no proxy object found in request.meta")

        proxy.callback(success=False)
        
        return None


    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
