# -*- coding: utf-8 -*-
import scrapy
import sys
import logging
import re
import json

from scrapy_autoproxy.proxy_objects import Proxy
from scrapy_autoproxy.storage_manager import StorageManager

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

class GatherproxySpider(scrapy.Spider):
    name = 'gatherproxy'
    allowed_domains = ['gatherproxy.com']
    start_urls = ['http://gatherproxy.com/']

    def __init__(self,*args,**kwargs):
        self.count = int(kwargs.get('count',1))
        self.storage_mgr = StorageManager()

    def start_requests(self):
        for i in range(self.count):
            request = scrapy.Request(url='http://www.gatherproxy.com/proxylistbycountry', dont_filter=True)
            logging.info("GET %s" % request.url)
            yield request

    def make_proxy(self,address,port,location,protocol='http'):
        port = int(port,16)
        self.storage_mgr.new_proxy(address,port,protocol)

    def log_proxy_info(self,proxy):
        log_str = """
        scraped proxy:
        ----------------
        ADDRESS: %s
        PORT: %s
        ----------------""" % (proxy.address, proxy.port)
        logging.info(log_str)

    def parse_list(self, response):
        script_elements = response.xpath('//script[contains(text(),"insertPrx")]').extract()
        for script_text in script_elements:
            proxy_data = json.loads(re.search(r'insertPrx\(([^\)]+)\);',script_text).group(1))
            self.make_proxy(proxy_data['PROXY_IP'], proxy_data['PROXY_PORT'], proxy_data['PROXY_COUNTRY'])

    def parse(self,response):
        links = response.xpath('//ul[@class="pc-list"]/li/a/@href').extract()

        for link in links:
            url = response.urljoin(link)
            yield scrapy.Request(url=url,callback=self.parse_list, dont_filter=True)
            