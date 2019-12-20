# -*- coding: utf-8 -*-
import scrapy
from IPython import embed
import logging
import sys
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class StreetscrapeSpider(scrapy.Spider):
    name = 'streetscrape'
    allowed_domains = ['proxycrawler.com']
    start_urls = ['https://api.dev.proxycrawler.com/proxy/test']

    def __init__(self,*args,**kwargs):
        self.count = int(kwargs.get('count',1))

    
    def start_requests(self):
        for i in range(self.count):
            request = scrapy.Request(url='https://api.dev.proxycrawler.com/proxy/test', dont_filter=True)
            logging.info("GET %s" % request.url)
            yield request
    

    def parse(self, response):

        logging.info("Response:")
        logging.info(response.body)
