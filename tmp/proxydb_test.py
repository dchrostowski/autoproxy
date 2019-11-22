import scrapy
from py_mini_racer import py_mini_racer
from IPython import embed
import base64
ctx = py_mini_racer.MiniRacer()


def get_mock_response():
    file_content = open('./proxydb.html','r').read()
    req = scrapy.Request(url='http://proxydb.net')
    return scrapy.http.response.html.HtmlResponse(
        url=req.url,
        request=req,
        body = file_content.encode('utf-8')
    )
    
def deobfuscate(resp):
    script_tds = resp.xpath('//div[@class="table-responsive"]/table[contains(@class,"table-hover")]//tr/td[1]')
    for td in script_tds:
        script = td.xpath('script/text()').extract_first()
        print("SCRIPT: %s " % script)
        embed()



resp = get_mock_response()
deobfuscate(resp)