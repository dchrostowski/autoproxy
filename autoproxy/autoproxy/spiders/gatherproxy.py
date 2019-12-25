# -*- coding: utf-8 -*-
import scrapy
import sys
import logging
from IPython import embed
import re
import json

from autoproxy.autoproxy_middleware.proxy_objects import Proxy
from autoproxy.autoproxy_middleware.storage_manager import StorageManager

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class GatherproxySpider(scrapy.Spider):
    name = 'gatherproxy'
    allowed_domains = ['gatherproxy.com']
    start_urls = ['http://gatherproxy.com/']

    def __init__(self,*args,**kwargs):
        self.count = int(kwargs.get('count',1))
        self.storage_mgr = StorageManager()

    def start_requests(self):
        for i in range(self.count):
            request = scrapy.Request(url='http://gatherproxy.com', dont_filter=True)
            logging.info("GET %s" % request.url)
            yield request

    def make_proxy(self,address,port,location,protocol='http'):
        port = int(port,16)
        proxy = Proxy(address=address,port=port)
        self.storage_mgr.new_proxy(proxy)
        return proxy

    def log_proxy_info(self,proxy):
        log_str = """
        scraped proxy:
        ----------------
        ADDRESS: %s
        PORT: %s
        ----------------""" % (proxy.address, proxy.port)
        logging.info(log_str)

    def parse(self, response):
        script_elements = response.xpath('//script[contains(text(),"insertPrx")]').extract()
        proxies = []
        for script_text in script_elements:
            proxy_data = json.loads(re.search(r'insertPrx\(([^\)]+)\);',script_text).group(1))
            proxies.append(self.make_proxy(proxy_data['PROXY_IP'], proxy_data['PROXY_PORT'], proxy_data['PROXY_COUNTRY']))

        
        for proxy in proxies:
            self.log_proxy_info(proxy)
            