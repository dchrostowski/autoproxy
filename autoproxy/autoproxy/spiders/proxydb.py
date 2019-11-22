# -*- coding: utf-8 -*-
import scrapy
import sys
import logging
from IPython import embed
import re
from py_mini_racer import py_mini_racer
from proxy_objects import Proxy
from storage_manager import StorageManager

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
        ctx.eval("const atob = (arg) => arg")
        rnnumt = resp.xpath('//div[@data-rnnumt]/@data-rnnumt').extract_first()
        ctx.eval("let rnnumt = %s" % rnnumt)
        
        trs = resp.xpath('//div[@class="table-responsive"]/table[contains(@class,"table-hover")]/tbody/tr')
        for tr in trs:
            script = tr.xpath('td[1]/script/text()').extract_first()
            string_to_replace = "(+document.querySelector('[data-rnnumt]').getAttribute('data-rnnumt'))"
            script = script.replace(string_to_replace, " rnnumt ")
            
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
        proxies = deobfuscate(response)
        
