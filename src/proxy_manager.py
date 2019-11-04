from util import parse_domain, flip_coin
from storage_manager import StorageManager, RedisDetailQueue
from autoproxy_config.config import configuration
from proxy_objects import ProxyObject
from datetime import datetime

app_config = lambda config_val: configuration.app_config[config_val]['value']

QUEUE_PREFIX = app_config('redis_queue_char')
PROXY_PREFIX = app_config('redis_proxy_char')
DETAIL_PREFIX = app_config('redis_detail_char')
BLACKLIST_THRESHOLD = app_config('blacklist_threshold')
DECREMENT_BLACKLIST = app_config('decrement_blacklist')
MAX_BLACKLIST_COUNT = app_config('max_blacklist_count')
SEED_FREQUENCY =  app_config('seed_frequency')
MIN_ACTIVE = app_config('min_active')
INACTIVE_PCT = app_config('inactive_pct')
SYNC_INTERVAL = app_config('sync_interval')
ACTIVE_PROXIES_PER_QUEUE = app_config('active_proxies_per_queue')
INACTIVE_PROXIES_PER_QUEUE = app_config('inactive_proxies_per_queue')
SEED_PROXIES_PER_QUEUE = app_config('seed_proxies_per_queue')
SEED_QUEUE_ID = app_config('seed_queue')



class ProxyManager(object):
    def __init__(self):
        self.storage_mgr = StorageManager()

    def get_proxy(self,request_url):
        domain = parse_domain(request_url)
        queue = self.storage_mgr.redis_mgr.get_queue_by_domain(domain)

        # TO DO, seed queue logic.
        if queue.id != SEED_QUEUE_ID and flip_coin(SEED_FREQUENCY):
            pass
        rdq_active = RedisDetailQueue(queue_key=queue.queue_key,active=True)
        rdq_inactive = RedisDetailQueue(queue_key=queue.queue_key,active=False)
        use_active = True
        draw_queue = rdq_active
        if rdq_active.length() < MIN_ACTIVE:
            draw_queue = rdq_inactive
        elif flip_coin(INACTIVE_PCT):
            draw_queue = rdq_inactive


            

        detail = draw_queue.dequeue(requeue=False)
        proxy = ProxyObject(self.storage_mgr, detail)

        proxy.dispatch(draw_queue)
        return proxy
        

