# -*- coding: utf-8 -*-
import scrapy
from IPython import embed

class ProxylistySpider(scrapy.Spider):
    name = 'proxylisty'
    allowed_domains = ['proxylisty.com']
    start_urls = ['http://www.proxylisty.com/ip-proxylist']

    def parse(self, response):

        trs = response.xpath('//div[@id="content"]//table[1]/tr[position()>1]')
        for tr in trs:
            tds = tr.xpath('td')
            address = tr.xpath('td[1]/text()').extract_first()
            port = tr.xpath('td[2]text()').extract_first()
            ptype = tr.xpath('td[3]/text()').extract_first()
            print(address)
            print(port)
            print(ptype)
            embed()
