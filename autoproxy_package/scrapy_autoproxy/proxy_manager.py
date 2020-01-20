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
MIN_QUEUE_SIZE = app_config('min_queue_size')
INACTIVE_PCT = app_config('inactive_pct')
SYNC_INTERVAL = app_config('sync_interval')
ACTIVE_PROXIES_PER_QUEUE = app_config('active_proxies_per_queue')
INACTIVE_PROXIES_PER_QUEUE = app_config('inactive_proxies_per_queue')
SEED_QUEUE_ID = app_config('seed_queue')
PROXY_INTERVAL = app_config('proxy_interval')



class ProxyManager(object):
    def __init__(self):
        self.storage_mgr = StorageManager()
        self.logger = logging.getLogger(__name__)

    def clone_seeds(self,target_queue):
        seed_queue = self.storage_mgr.get_seed_queue()
        if target_queue.queue_id == seed_queue.queue_id:
            raise Exception("CANNOT CLONE SEED TO SEED")
        
        seed_details = self.storage_mgr.redis_mgr.get_all_queue_details(seed_queue.queue_key)

        for seed_detail in seed_details:
            self.storage_mgr.clone_detail(seed_detail,target_queue)

        active_rdq = RedisDetailQueue(target_queue.queue_key,active=True)
        inactive_rdq = RedisDetailQueue(target_queue.queue_key,active=False)

        active_rdq.reload()
        inactive_rdq.reload()


    def dequeue_and_clone_seed(self,target_queue,active=True):
        seed_rdq = RedisDetailQueue(self.storage_mgr.get_seed_queue().queue_key, active=active)
        seed = seed_rdq.dequeue(requeue=True)
        cloned = self.storage_mgr.clone_detail(seed,target_queue)
        return cloned


    def get_proxy(self,request_url):
        domain = parse_domain(request_url)
        queue = self.storage_mgr.redis_mgr.get_queue_by_domain(domain)
        if len(self.storage_mgr.redis_mgr.get_all_queue_details(queue.queue_key)) == 0:
            seed_details = self.storage_mgr.db_mgr.get_non_seed_details(queue.queue_id)
            if len(seed_details) == 0:
                self.clone_seeds(queue)
            
            else:
                for seed_detail in seed_details:
                    self.storage_mgr.redis_mgr.register_detail(seed_detail)

        
        
        rdq_active = RedisDetailQueue(queue_key=queue.queue_key,active=True)
        rdq_inactive = RedisDetailQueue(queue_key=queue.queue_key,active=False)


        self.logger.info("active queue count: %s" % rdq_active.length())
        self.logger.info("inactive queue count: %s" % rdq_inactive.length())

        use_active = True
        
                

        if rdq_inactive.length() < MIN_QUEUE_SIZE and queue.queue_id != SEED_QUEUE_ID:
            rdq_inactive.clear()
            self.clone_seeds(target_queue=queue)
            

        if rdq_active.length() < MIN_QUEUE_SIZE:
            use_active=False
            
        
        elif flip_coin(INACTIVE_PCT):
            use_active = False
        
        
        if use_active:
            self.logger.info("using active queue")
            draw_queue = rdq_active
        
        else:
            self.logger.info("using inactive queue")
            draw_queue = rdq_inactive
        
        detail = None

        if flip_coin(SEED_FREQUENCY):
            logging.info("FLIP COIN RETURNED TRUE")
            detail = self.dequeue_and_clone_seed(queue)
        else:
            detail = draw_queue.dequeue(requeue=False)
        
        
        now = datetime.utcnow()
        elapsed_time = now - detail.last_used
        if elapsed_time.seconds < PROXY_INTERVAL:
            while elapsed_time.seconds < PROXY_INTERVAL and draw_queue.length() > MIN_QUEUE_SIZE:
                logging.debug("draw queue key: %s, active: %s" % (draw_queue.queue_key, draw_queue.active))
                logging.warn("Proxy id %s was last used %s seconds ago, using a different proxy." % (detail.proxy_id, elapsed_time.seconds))
                detail = draw_queue.dequeue(requeue=False)
                now  = datetime.utcnow()
                elapsed_time = now  - detail.last_used
        
        
        proxy = ProxyObject(self.storage_mgr, detail)


        proxy.dispatch(rdq_active,rdq_inactive)
        return proxy
        

    def new_proxy(self,proxy):
        return self.storage_mgr.new_proxy(proxy)
        