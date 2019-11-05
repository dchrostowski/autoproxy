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

    def load_from_seed_queue(self,queue,num=None):
        if queue.queue_id == SEED_QUEUE_ID:
            return

        seed_queue = self.storage_mgr.redis_mgr.get_queue_by_id(SEED_QUEUE_ID)
        seed_rdq_active = RedisDetailQueue(queue_key=seed_queue.queue_key,active=True)
        seed_rdq_inactive = RedisDetailQueue(queue_key=seed_queue.queue_key, active=False)

        
        active_seeds_to_dequeue = min(ACTIVE_PROXIES_PER_QUEUE,seed_rdq_active.length())
        inactive_seeds_to_dequeue = INACTIVE_PROXIES_PER_QUEUE - active_seeds_to_dequeue

        if num is not None:
            active_seeds_to_dequeue = num
            inactive_seeds_to_dequeue = num
        
        for i in range(active_seeds_to_dequeue):
            try:
                self.storage_mgr.clone_detail(seed_rdq_active.dequeue(), queue)
            except Exception as e:
                pass
        
        for i in range(inactive_seeds_to_dequeue):
            self.storage_mgr.clone_detail(seed_rdq_inactive.dequeue(), queue)

        


    def get_seed_proxy(self,queue):
        if queue.id == SEED_QUEUE_ID:
            logging.warn("trying to copy seed proxy to seed_queue")
            return

        seed_queue = self.storage_mgr.redis_mgr.get_queue_by_id(SEED_QUEUE_ID)
        self.storage_mgr.clone_detail(seed_queue.dequeue(), queue)

        
        

    def get_proxy(self,request_url):
        domain = parse_domain(request_url)
        queue = self.storage_mgr.redis_mgr.get_queue_by_domain(domain)
        rdq_active = RedisDetailQueue(queue_key=queue.queue_key,active=True)
        rdq_inactive = RedisDetailQueue(queue_key=queue.queue_key,active=False)

        use_active = True
        clone_seed = flip_coin(SEED_FREQUENCY)

        if rdq_inactive.length() < MIN_ACTIVE:
            self.load_from_seed_queue(queue)

        if clone_seed:
            self.load_from_seed_queue(queue,num=1)

        if rdq_active.length() < MIN_ACTIVE:
            use_active = False
        else:
            if flip_coin(INACTIVE_PCT):
                use_active = False
        
        
        if use_active and rdq_active.length() > 0:
            draw_queue = rdq_active
        
        else:
            draw_queue = rdq_inactive
        
        detail = None

        print("queue length: %s" % rdq_inactive.length())
        try:
            detail = draw_queue.dequeue(requeue=False)
        except Exception as e:
            embed()
            raise(e)

        proxy = ProxyObject(self.storage_mgr, detail)

        proxy.dispatch(rdq_active,rdq_inactive)
        return proxy
        

