from scrapy_autoproxy.config import configuration
from scrapy_autoproxy.storage_manager import StorageManager, Redis
from scrapy_autoproxy.proxy_manager import ProxyManager
from IPython import embed

redis = Redis(**configuration.redis_config)
redis.flushall()

sm = StorageManager()
pm = ProxyManager()

for i in range(100):
    proxy = pm.get_proxy('https://foobarbaz.com')
    proxy.callback(success=True)
    