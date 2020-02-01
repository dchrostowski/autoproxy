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

    def get_seed_proxy(self):
        return None

    def get_proxy(self,request_url):
        domain = parse_domain(request_url)
        # get the queue for the request url's domain. If a queue doesn't exist, one will be created.
        queue = self.storage_mgr.redis_mgr.get_queue_by_domain(domain)
        if queue.id() == SEED_QUEUE_ID:
            return self.get_seed_proxy()
        
        # self logger name to requst url domain
        self.logger = logging.getLogger(queue.domain)
        
        # first get all details that may already be in redis
        # TODO, change this to a simple count

        num_details = self.storage_mgr.redis_mgr.get_queue_count(queue)
        #logging.debug("\n\n\n\n\nafter get num details for queue")
        
        
        
        if num_details == 0:
            self.storage_mgr.redis_mgr.initialize_queuequeue=(queue)
        
        rdq_active = RedisDetailQueue(queue,active=True)
        rdq_inactive = RedisDetailQueue(queue,active=False)
        not_enqueued = (num_details - (rdq_active.length() + rdq_inactive.length()))
        self.logger.info("----------------------------------------------")
        self.logger.info(" Cached total   : %s" % num_details)
        self.logger.info(" Not enqueued   : %s" % not_enqueued)
        self.logger.info(" Active RDQ     : %s" % rdq_active.length())
        self.logger.info(" Inactive RDQ   : %s" % rdq_inactive.length())
        self.logger.info("----------------------------------------------")

        if rdq_inactive.length() < MIN_QUEUE_SIZE:
            logging.info("rdq is less than the min queue size, creating some new details...")
            self.storage_mgr.create_new_details(queue=queue)
            # will return a list of new seed details that have not yet been used for this queue

        elif flip_coin(SEED_FREQUENCY):
            self.storage_mgr.create_new_details(queue=queue,count=1)

        use_active = True

        if rdq_active.length() < MIN_QUEUE_SIZE:
            use_active=False
            
        
        elif flip_coin(INACTIVE_PCT):
            use_active = False

        draw_queue = None
        
        if use_active:
            self.logger.info("using active queue")
            draw_queue = rdq_active
        
        else:
            self.logger.info("using inactive queue")
            draw_queue = rdq_inactive
        
        
        detail = draw_queue.dequeue()
        proxy = ProxyObject(detail, StorageManager(), draw_queue)
        
        now = datetime.utcnow()
        elapsed_time = now - proxy.detail.last_used
        if elapsed_time.seconds < PROXY_INTERVAL:
            self.logger.debug("Proxy %s was last used against %s %s seconds ago, using a different proxy." % (proxy.address, domain, elapsed_time.seconds))
            return self.get_proxy(request_url)            
        
        self.logger.info("dispatching proxy %s" % proxy.address)
        proxy.dispatch()
        return proxy
        
        

    def new_proxy(self,proxy):
        return self.storage_mgr.new_proxy(proxy)
        