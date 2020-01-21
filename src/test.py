from scrapy_autoproxy.proxy_manager import ProxyManager
from scrapy_autoproxy.storage_manager import RedisDetailQueue, StorageManager
from scrapy_autoproxy.util import parse_domain

from IPython import embed
def get_pm():
    return ProxyManager()

def get_redis():
    return ProxyManager().storage_mgr.redis_mgr.redis

def get_sm():
    return StorageManager()

def get_redis_detail_queue(url):
    sm = get_sm()
    domain = parse_domain(url)
    queue = sm.redis_mgr.get_queue_by_domain(domain)
    rdq_active = RedisDetailQueue(queue.queue_key, active=True)
    rdq_inactive = RedisDetailQueue(queue.queue_key, active=True)

    return {'active': rdq_active, 'inactive': rdq_inactive}




redis = get_redis()
pm = get_pm()
embed()