# -*- coding: utf-8 -*-
import scrapy
import sys
import base64
import logging
from IPython import embed
import re
from py_mini_racer import py_mini_racer
from proxy_objects import Proxy
from storage_manager import StorageManager

ctx = py_mini_racer.MiniRacer()
ctx.eval(" var atob = (arg) => arg ")

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class ProxydbSpider(scrapy.Spider):
    name = 'proxydb'
    allowed_domains = ['proxydb.net']
    start_urls = ['http://proxydb.net/']

    def __init__(self,*args,**kwargs):
        self.count = int(kwargs.get('count',1))
        self.storage_mgr = StorageManager()
    
    def start_requests(self):
        for i in range(self.count):
            request = scrapy.Request(url='http://proxydb.net/', dont_filter=True)
            logging.info("GET %s" % request.url)

            yield request

    def deobfuscate(self,resp):
        proxies = []
        try:
            trs = resp.xpath('//div[@class="table-responsive"]/table[contains(@class,"table-hover")]/tbody/tr')
            
            for tr in trs:
                script = tr.xpath('td[1]/script/text()').extract_first()
                rnnum_var_full_search = re.search(r'getAttribute\(\'(data\-(\w+))\'\)',script)

                rnnum_var_full = rnnum_var_full_search.group(1)
                rnnum_var = rnnum_var_full_search.group(2)
                
                rnnum = resp.xpath('//div[@%s]/@%s' % (rnnum_var_full,rnnum_var_full)).extract_first()
                string_to_replace = "(+document.querySelector('[%s]').getAttribute('%s'))" % (rnnum_var_full,rnnum_var_full)
                
                ctx.eval(" var %s = %s " % (rnnum_var,rnnum))

                script = script.replace(string_to_replace, " %s " % rnnum_var)
                
                scripts = script.split(';')[0:3]
                var_re = r'var\s+(\w+)\s*\='

                addr1_var = re.search(var_re, scripts[0]).group(1)
                addr2_var = re.search(var_re, scripts[1]).group(1)
                port_var = re.search(var_re, scripts[2]).group(1)

                for js in scripts:
                    ctx.eval(js)

                addr1 = ctx.eval(addr1_var)
                addr2 = base64.b64decode(ctx.eval(addr2_var)).decode('utf-8')
                port = int(ctx.eval(port_var))

                address = "%s%s" % (addr1,addr2)
                protocol = tr.xpath('td[5]/text()').extract_first().strip().lower()
                logging.info("successfully deobfuscated proxy:\naddress=%s port=%s protocol=%s" % (address,port, protocol))
                proxies.append({ 'address': address, 'port':port, 'protocol': protocol })

        except Exception as e:
            logging.warn(e)

        return proxies

    def parse(self,response):
        proxies = self.deobfuscate(response)
        for pdata in proxies:
            proxy = Proxy(address=pdata['address'], port=pdata['port'],protocol=pdata['protocol'])
            self.storage_mgr.new_proxy(proxy)
        
        proxies_by_dropdown_urls = response.xpath('//div[@aria-labelledby="navbar_dropdown_proxies_by"]/a/@href').extract()
        for url in proxies_by_dropdown_urls:
            url = response.urljoin(url)
            req = scrapy.Request(url=url, callback=self.parse_dropdown, dont_filter=True)
            yield req

    def parse_dropdown(self,response):
        links = response.xpath('//table[contains(@class,"table-hover")]/tbody/tr/td[1]/a/@href').extract()
        for link in links:
            url = response.urljoin(link)
            req = scrapy.Request(url=url, callback=self.parse_category_links)
            yield req



    def parse_category_links(self,response):
        print("parsing cat link")
        proxies = self.deobfuscate(response)
        for pdata in proxies:
            proxy = Proxy(address=pdata['address'], port=pdata['port'],protocol=pdata['protocol'])
            self.storage_mgr.new_proxy(proxy)
