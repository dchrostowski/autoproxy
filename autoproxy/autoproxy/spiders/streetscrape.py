# -*- coding: utf-8 -*-
import scrapy
from IPython import embed

class StreetscrapeSpider(scrapy.Spider):
    name = 'streetscrape'
    allowed_domains = ['streetscrape.com']
    start_urls = ['https://api.dev.proxycrawler.com/proxy/test']


    def start_requests(self):
        for i in range(100):
            request = scrapy.Request(url='https://api.dev.proxycrawler.com/proxy/test', dont_filter=True)
            yield request


    def parse(self, response):
        print(response)
