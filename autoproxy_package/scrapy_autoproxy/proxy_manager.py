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
        self.logger.info("clone_seeds: in clone_seeds")
        seed_queue = self.storage_mgr.get_seed_queue()
        self.logger.info("clone_seeds: check seed queue")
        if target_queue.queue_id == seed_queue.queue_id:
            raise Exception("CANNOT CLONE SEED TO SEED")
        
        seed_details = self.storage_mgr.redis_mgr.get_all_queue_details(seed_queue.queue_key)
        self.logger.info("clone_seeds, check seed_details\n\n")

        for seed_detail in seed_details:
            self.logger.info("for seed_detail in seed_details\n\n")
            self.storage_mgr.clone_detail(seed_detail,target_queue)

        active_rdq = RedisDetailQueue(target_queue.queue_key,active=True)
        inactive_rdq = RedisDetailQueue(target_queue.queue_key,active=False)

        self.logger.info("clone_seeds: active and inactive rdq created\n\n")
        embed()

        active_rdq.reload()
        self.logger.info("clone_sedds: after active_rdq.reload()\n\n")
        embed()
        inactive_rdq.reload()
        self.logger.info("clone_seeds: after inactive\n\n")
        

        embed()


    def dequeue_and_clone_seed(self,target_queue,active=True):
        seed_rdq = RedisDetailQueue(self.storage_mgr.get_seed_queue().queue_key, active=active)

        seed = seed_rdq.dequeue(requeue=True)
        cloned = self.storage_mgr.clone_detail(seed,target_queue)
        return cloned


    def get_proxy(self,request_url):
        domain = parse_domain(request_url)
        # get the queue for the request url's domain. If a queue doesn't exist, one will be created.
        queue = self.storage_mgr.redis_mgr.get_queue_by_domain(domain)
        # self logger name to requst url domain
        self.logger = logging.getLogger(queue.domain)
        
        # first get all details that may already be in redis
        all_queue_details = self.storage_mgr.redis_mgr.get_all_queue_details(queue.queue_key)
        
        if len(all_queue_details) == 0:
            if queue.queue_id == SEED_QUEUE_ID:
                # TODO - maybe throw an exception here because this shouldn't happen.
                pass
            else:
                self.logger.info("no queue details, getting some from the database\n\n")
                # will return a list of new seed details that have not yet been used for this queue
                new_queue_details = self.storage_mgr.db_mgr.get_unused_seed_details(queue.queue_id)
                self.logger("got %s unused seed details" % len(new_queue_details))
            self.logger.info(len(seed_details))
            if len(seed_details) == 0:
                self.logger.info("There are no details in the database for %s queue\n\n" % queue.domain)
                self.clone_seeds(queue)
            
            else:
                self.logger.info("Registering details from database to redis\n\n")
                for seed_detail in seed_details:
                    self.storage_mgr.redis_mgr.register_detail(seed_detail)
                
                embed()

        
        
        rdq_active = RedisDetailQueue(queue_key=queue.queue_key,active=True)
        rdq_inactive = RedisDetailQueue(queue_key=queue.queue_key,active=False)

        if rdq_active.length() == 0:
            rdq_active.reload()

        if rdq_inactive.length() == 0:
            rdq_inactive.reload()
            
        self.logger.info("get_proxy: rdqs created\n\n")
        embed()
        

        self.logger.info("active queue count: %s" % rdq_active.length())
        self.logger.info("inactive queue count: %s\n\n" % rdq_inactive.length())

        embed()
        use_active = True
        
                

        if rdq_inactive.length() < MIN_QUEUE_SIZE and queue.queue_id != SEED_QUEUE_ID:
            self.logger.info("rdq_inactive.length() < MIN_QUEUE_SIZE")
            embed()
            rdq_inactive.clear()
            self.logger.info("cleared rdq_inactive, about to clone seeds")
            embed()
            self.logger.info("cloning seeds...")
            self.clone_seeds(target_queue=queue)

        logging.info("get_proxy: after clone stuff\n\n")
        embed()
            

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
            self.logger.debug("FLIP COIN RETURNED TRUE")
            detail = self.dequeue_and_clone_seed(queue)
        else:
            detail = draw_queue.dequeue(requeue=False)
        
        
        now = datetime.utcnow()
        elapsed_time = now - detail.last_used
        if elapsed_time.seconds < PROXY_INTERVAL:
            while elapsed_time.seconds < PROXY_INTERVAL and draw_queue.length() > MIN_QUEUE_SIZE:
                self.logger.debug("draw queue key: %s, active: %s" % (draw_queue.queue_key, draw_queue.active))
                self.logger.debug("Proxy id %s was last used %s seconds ago, using a different proxy." % (detail.proxy_id, elapsed_time.seconds))
                detail = draw_queue.dequeue(requeue=False)
                now  = datetime.utcnow()
                elapsed_time = now  - detail.last_used
        
        
        proxy = ProxyObject(self.storage_mgr, detail)


        proxy.dispatch(rdq_active,rdq_inactive)
        return proxy
        

    def new_proxy(self,proxy):
        return self.storage_mgr.new_proxy(proxy)
        