import sys
import logging
import scrapy
from py_mini_racer import py_mini_racer
from IPython import embed
import base64
import re

ctx = py_mini_racer.MiniRacer()
logging.basicConfig(stream=sys.stdout, level=logging.INFO)



def get_mock_response():
    file_content = open('./proxydb.html','r').read()
    req = scrapy.Request(url='http://proxydb.net')
    return scrapy.http.response.html.HtmlResponse(
        url=req.url,
        request=req,
        body = file_content.encode('utf-8')
    
    )

def replace_str_dict():
    return {
        "(+document.querySelector('[data-rnnumt]').getAttribute('data-rnnumt'))": " rnnumtt ",

    }


def eval_block(block):
    ctx.eval(block)
    
def deobfuscate(resp):


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




resp = get_mock_response()
deobfuscate(resp)