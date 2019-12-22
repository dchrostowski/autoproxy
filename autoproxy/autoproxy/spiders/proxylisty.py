# -*- coding: utf-8 -*-
import scrapy
from IPython import embed
from storage_manager import StorageManager
from proxy_objects import Proxy

class ProxylistySpider(scrapy.Spider):
    name = 'proxylisty'
    allowed_domains = ['proxylisty.com']
    start_urls = ['http://www.proxylisty.com/ip-proxylist']

    def __init__(self,*args,**kwargs):
        self.count = int(kwargs.get('count',1))
        self.storage_mgr = StorageManager()

    def start_requests(self):
        for i in range(self.count):
            request = scrapy.Request(url='http://www.proxylisty.com/ip-proxylist', dont_filter=True)
            logging.info("GET %s" % request.url)

            yield request

    def parse(self, response):

        trs = response.xpath('//div[@id="content"]//table[1]/tr[position()>1]')
        for tr in trs:
            tds = tr.xpath('td')
            address = tr.xpath('td[1]/text()').extract_first()
            port = tr.xpath('td[2]/a/text()').extract_first()
            protocol = tr.xpath('td[3]/text()').extract_first()

            if address is not None and port is not None and protocol is not None:
                try:
                    proxy = Proxy(address=address,port=int(port),protocol=protocol.lower())
                    print(proxy)
                    self.storage_mgr.new_proxy(proxy)
                except:
                    pass


        
        next_link = response.xpath('//div[@id="content"]//table[1]/tr/td[@colspan="9"]/ul/li/a[text()="Next"]/@href').extract_first()
        if next_link is not None:
            yield scrapy.Request(url=response.urljoin(next_link),callback=self.parse)
            
            
