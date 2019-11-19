from util import parse_domain, flip_coin
from storage_manager import StorageManager, RedisDetailQueue
from autoproxy_config.config import configuration
from proxy_objects import ProxyObject
from datetime import datetime
import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
from IPython import embed

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

    def load_seeds(self,queue,active=False,num=0):
        seed_queue = self.storage_mgr.redis_mgr.get_queue_by_id(SEED_QUEUE_ID)
        seed_rdq = RedisDetailQueue(queue_key=seed_queue.queue_key,active=active)
        seed_rdq_size = seed_rdq.length()
        seeds_to_dequeue = 0
        if num > 0:
            seeds_to_dequeue = min(num,seed_rdq_size)
        elif active and num == 0:
            seeds_to_dequeue = min(ACTIVE_PROXIES_PER_QUEUE,seed_rdq_size)
        elif not active and num == 0:
            seeds_to_dequeue = min(INACTIVE_PROXIES_PER_QUEUE, seed_rdq_size)
        
        for i in range(seeds_to_dequeue):
            self.storage_mgr.clone_detail(seed_rdq.dequeue(), queue)

        
        

    def get_proxy(self,request_url):
        domain = parse_domain(request_url)
        queue = self.storage_mgr.redis_mgr.get_queue_by_domain(domain)
        rdq_active = RedisDetailQueue(queue_key=queue.queue_key,active=True)
        rdq_inactive = RedisDetailQueue(queue_key=queue.queue_key,active=False)

        logging.info("active queue count: %s" % rdq_active.length())
        logging.info("inactive queue count: %s" % rdq_inactive.length())

        use_active = True
        clone_seed = flip_coin(SEED_FREQUENCY)

        if rdq_active.length() < ACTIVE_PROXIES_PER_QUEUE:
            self.load_seeds(queue,active=True)

        if rdq_inactive.length() < INACTIVE_PROXIES_PER_QUEUE:
            self.load_seeds(queue,active=False)

        if clone_seed:
            self.load_from_seed_queue(queue, active=True, num=1)
            self.load_from_seed_queue(queue, active=False, num=1)


        if rdq_active.length() < MIN_ACTIVE:
            use_active = False
        
        if flip_coin(INACTIVE_PCT):
            use_active = False
        
        
        if use_active and rdq_active.length() > 0:
            logging.info("using active queue")
            draw_queue = rdq_active
        
        else:
            logging.info("using inactive queue")
            draw_queue = rdq_inactive
        
        detail = None
        
        detail = draw_queue.dequeue(requeue=False)
        proxy = ProxyObject(self.storage_mgr, detail)
        proxy.dispatch(rdq_active,rdq_inactive)
        return proxy
        

    def new_proxy(self,proxy):
        return self.storage_mgr.new_proxy(proxy)
        