from util import parse_domain, flip_coin
from storage_manager import StorageManager, RedisDetailQueue
from autoproxy_config.config import configuration
from proxy_objects import ProxyObject

INACTIVE_PCT = configuration.app_config['inactive_pct']['value']
MIN_ACTIVE = configuration.app_config['min_active']['value']


class ProxyManager(object):
    def __init__(self):
        self.storage_mgr = StorageManager()

    def get_proxy(self,request_url):
        domain = parse_domain(request_url)
        queue = self.storage_mgr.redis_mgr.get_queue_by_domain(domain)
        rdq_active = RedisDetailQueue(queue_key=queue.queue_key,active=True)
        rdq_inactive = RedisDetailQueue(queue_key=queue.queue_key,active=False)
        use_active = True
        draw_queue = rdq_active
        if rdq_active.length() < MIN_ACTIVE:
            draw_queue = rdq_inactive
        else:
            if flip_coin(INACTIVE_PCT):
                draw_queue = rdq_inactive

        detail = draw_queue.dequeue()
        proxy = ProxyObject(self.storage_mgr, detail)

        proxy.dispatch()
        return proxy
        

