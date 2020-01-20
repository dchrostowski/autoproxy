from scrapy_autoproxy.util import parse_domain, flip_coin
from scrapy_autoproxy.storage_manager import StorageManager, RedisDetailQueue
from scrapy_autoproxy.config import configuration
from scrapy_autoproxy.proxy_objects import ProxyObject
from datetime import datetime
import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
from IPython import embed

app_config = lambda config_val: configuration.app_config[config_val]['value']

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
PROXY_INTERVAL = app_config('proxy_interval')



class ProxyManager(object):
    def __init__(self):
        self.storage_mgr = StorageManager()
        self.logger = logging.getLogger(__name__)

    def load_seeds(self,target_queue,num=0):
        seed_queue = self.storage_mgr.redis_mgr.get_queue_by_id(SEED_QUEUE_ID)
        active_seed_rdq = RedisDetailQueue(queue_key=seed_queue.queue_key,active=True)
        inactive_seed_rdq = RedisDetailQueue(queue_key=seed_queue.queue_key,active=False)
        
        active_seeds_to_dequeue = 0
        inactive_seeds_to_dequeue = 0

        active_target_rdq = RedisDetailQueue(queue_key=target_queue.queue_key, active=True)
        inactive_target_rdq = RedisDetailQueue(queue_key=target_queue.queue_key, active=False)
        
        if num > 0:
            active_seeds_to_dequeue = min(num,active_seed_rdq.length())
            inactive_seeds_to_dequeue = min(num,inactive_seed_rdq.length())
        
        else:
            active_seeds_to_dequeue = min(ACTIVE_PROXIES_PER_QUEUE, active_seed_rdq.length())
            inactive_seeds_to_dequeue = min(INACTIVE_PROXIES_PER_QUEUE, inactive_seed_rdq.length())
        
        for i in range(active_seeds_to_dequeue):
            new_detail = self.storage_mgr.clone_detail(active_seed_rdq.dequeue(), target_queue)
            inactive_target_rdq.enqueue(new_detail)
        for i in range(inactive_seeds_to_dequeue):
            new_detail = self.storage_mgr.clone_detail(inactive_seed_rdq.dequeue(), target_queue)
            inactive_target_rdq.enqueue(new_detail)  
        

    def get_proxy(self,request_url):
        domain = parse_domain(request_url)
        queue = self.storage_mgr.redis_mgr.get_queue_by_domain(domain)
        
        rdq_active = RedisDetailQueue(queue_key=queue.queue_key,active=True)
        rdq_inactive = RedisDetailQueue(queue_key=queue.queue_key,active=False)


        self.logger.info("active queue count: %s" % rdq_active.length())
        self.logger.info("inactive queue count: %s" % rdq_inactive.length())

        use_active = True
        clone_seed = flip_coin(SEED_FREQUENCY)

        if rdq_inactive.length() < 1:
            self.load_seeds(target_queue=queue)

        if clone_seed:
            self.load_seeds(target_queue=queue, num=1)


        if rdq_active.length() < MIN_ACTIVE:
            use_active=False
            
        
        elif flip_coin(INACTIVE_PCT):
            use_active = False
        
        
        if use_active and rdq_active.length() > 0:
            self.logger.info("using active queue")
            draw_queue = rdq_active
        
        else:
            self.logger.info("using inactive queue")
            draw_queue = rdq_inactive
        
        
        detail = draw_queue.dequeue(requeue=False)
        now = datetime.utcnow()
        elapsed_time = now - detail.last_used
        if elapsed_time.seconds < PROXY_INTERVAL:
            while elapsed_time.seconds < PROXY_INTERVAL:
                logging.warn("Proxy was last used %s seconds ago, using a different proxy." % elapsed_time.seconds)
                draw_queue.enqueue(detail)
                detail = draw_queue.dequeue(requeue=False)
                now  = datetime.utcnow()
                elapsed_time = now  - detail.last_used
        
        
        proxy = ProxyObject(self.storage_mgr, detail)
        while 'socks' in proxy.protocol:
            detail = draw_queue.dequeue(requeue=False)
            proxy = ProxyObject(self.storage_mgr, detail)


        proxy.dispatch(rdq_active,rdq_inactive)
        return proxy
        

    def new_proxy(self,proxy):
        return self.storage_mgr.new_proxy(proxy)
        