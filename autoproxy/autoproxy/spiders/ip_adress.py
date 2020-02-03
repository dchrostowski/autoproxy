# -*- coding: utf-8 -*-
import scrapy
import sys
import logging
import re
import json
from scrapy_autoproxy.proxy_objects import Proxy
from scrapy_autoproxy.storage_manager import StorageManager

class IpAdressSpider(scrapy.Spider):
    name = 'ip-adress'
    allowed_domains = ['ip-adress.com']
    start_urls = ['https://www.ip-adress.com/proxy-list']

    def __init__(self,*args,**kwargs):
        self.count = int(kwargs.get('count',1))
        self.storage_mgr = StorageManager()
    
    def start_requests(self):
        for i in range(self.count):
            request = scrapy.Request(url='https://www.ip-adress.com/proxy-list', dont_filter=True)
            logging.info("GET %s" % request.url)
            yield request

    def parse(self, response):
        trs = response.xpath('//table[contains(@class,"proxylist")]//tr[position() > 1]')
        for tr in trs:
            address = tr.xpath('td[1]/a/text()').extract_first()
            port = tr.xpath('td[1]/text()').extract_first()
            port = re.search(r'(\d+)', port).group(1)
            self.storage_mgr.new_proxy(address,port)            
