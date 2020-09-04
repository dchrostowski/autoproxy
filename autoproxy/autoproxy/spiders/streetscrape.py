# -*- coding: utf-8 -*-
import scrapy

import logging
import sys
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
from scrapy.utils.project import get_project_settings


class StreetscrapeSpider(scrapy.Spider):
    name = 'streetscrape'
    allowed_domains = ['proxycrawler.com']
    start_urls = ['https://api.dev.proxycrawler.com/proxy/test']

    def __init__(self,*args,**kwargs):
        logging.info("%s started." % self.name)
        
    

    def parse(self, response):

        logging.info("Response:")
        logging.info(response.body_as_unicode())
