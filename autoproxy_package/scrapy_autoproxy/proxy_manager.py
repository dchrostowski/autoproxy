from scrapy_autoproxy.util import parse_domain, flip_coin
from scrapy_autoproxy.storage_manager import StorageManager, RedisDetailQueue
from scrapy_autoproxy.config import configuration
from scrapy_autoproxy.proxy_objects import ProxyObject
from datetime import datetime
import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
import time

app_config = lambda config_val: configuration.app_config[config_val]['value']

BLACKLIST_THRESHOLD = app_config('blacklist_threshold')
DECREMENT_BLACKLIST = app_config('decrement_blacklist')
MAX_BLACKLIST_COUNT = app_config('max_blacklist_count')
SEED_FREQUENCY =  app_config('seed_frequency')
MIN_QUEUE_SIZE = app_config('min_queue_size')
INACTIVE_PCT = app_config('inactive_pct')
ACTIVE_PROXIES_PER_QUEUE = app_config('active_proxies_per_queue')
INACTIVE_PROXIES_PER_QUEUE = app_config('inactive_proxies_per_queue')
SEED_QUEUE_ID = app_config('seed_queue')
PROXY_INTERVAL = app_config('proxy_interval')

import logging


class ProxyManager(object):
    def __init__(self):
        self.storage_mgr = StorageManager()
        self.logger = logging.getLogger(__name__)

    def get_proxy(self,request_url):
        is_seed = False
        domain = parse_domain(request_url)
        # get the queue for the request url's domain. If a queue doesn't exist, one will be created.
        queue = self.storage_mgr.redis_mgr.get_queue_by_domain(domain)
        
        if queue.id() == SEED_QUEUE_ID:
            is_seed = True
        
        # self logger name to requst url domain
        self.logger = logging.getLogger(queue.domain)
        
        # first get all details that may already be in redis
        # TODO, change this to a simple count

        num_details = self.storage_mgr.redis_mgr.get_queue_count(queue)
        #logging.debug("\n\n\n\n\nafter get num details for queue")
        
        
        if num_details == 0 and is_seed:
            self.storage_mgr.initialize_seed_queue()
        
        if num_details == 0 and not is_seed:
            self.storage_mgr.redis_mgr.initialize_queue(queue=queue)
        
        rdq_active = RedisDetailQueue(queue,active=True)
        rdq_inactive = RedisDetailQueue(queue,active=False)
        num_enqueued = rdq_active.length() + rdq_inactive.length()

        not_enqueued = num_details - num_enqueued
        logging.info("""
        ------------------------------------|
        --------------| Cached total   : %s |
        --------------| Not enqueued   : %s |
        --- ----------| Active RDQ     : %s |
        --------------| Inactive RDQ   : %s |
        -----------------------------------------------|
        """ % (num_details,not_enqueued,rdq_active.length(),rdq_inactive.length()))

        if rdq_inactive.length() < MIN_QUEUE_SIZE and not is_seed:
            self.logger.info("rdq is less than the min queue size, creating some new details...")
            self.storage_mgr.create_new_details(queue=queue)
            # will return a list of new seed details that have not yet been used for this queue

        elif flip_coin(SEED_FREQUENCY) and not is_seed:
            self.storage_mgr.create_new_details(queue=queue,count=1)

        use_active = True

        if rdq_active.length() < MIN_QUEUE_SIZE:
            use_active=False
            
        
        elif flip_coin(INACTIVE_PCT):
            use_active = False

        draw_queue = None
        
        if use_active:
            self.logger.info("using active RDQ")
            draw_queue = rdq_active
        
        else:
            self.logger.info("using inactive RDQ")
            draw_queue = rdq_inactive
        
        
        detail = draw_queue.dequeue()
        proxy = ProxyObject(detail, StorageManager(), draw_queue)
        
        now = datetime.utcnow()
        elapsed_time = now - proxy.detail.last_used
        if elapsed_time.seconds < PROXY_INTERVAL:
            self.logger.warn("Proxy %s was last used against %s %s seconds ago, using a different proxy." % (proxy.address, domain, elapsed_time.seconds))
            return self.get_proxy(request_url)            
        
        proxy.dispatch()
        return proxy
        
        

    def new_proxy(self,address,port,protocol='http'):
        return self.storage_mgr.new_proxy(address,port,protocol)
        