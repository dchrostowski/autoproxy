
from datetime import datetime
import time
from random import randint
import inspect
import re
import sys

from scrapy_autoproxy.config import configuration
from scrapy_autoproxy.util import format_redis_boolean, format_redis_timestamp, parse_boolean, parse_timestamp

DEFAULT_TIMESTAMP = datetime.fromtimestamp(946684800)
BOOLEAN_VALS = (True,'1',False,'0')
app_config = lambda config_val: configuration.app_config[config_val]['value']


BLACKLIST_THRESHOLD = app_config('blacklist_threshold')
DECREMENT_BLACKLIST = app_config('decrement_blacklist')
MAX_BLACKLIST_COUNT = app_config('max_blacklist_count')
SEED_FREQUENCY =  app_config('seed_frequency')
INACTIVE_PCT = app_config('inactive_pct')
ACTIVE_PROXIES_PER_QUEUE = app_config('active_proxies_per_queue')
INACTIVE_PROXIES_PER_QUEUE = app_config('inactive_proxies_per_queue')
import logging

class Proxy(object):
    AVAILABLE_PROTOCOLS = ('http', 'https', 'socks5', 'socks4')

    def __init__(self, address, port, protocol='http', proxy_id=None, proxy_key=None):
        self.address = address
        self.port = int(port)
        protocol = protocol.lower()
        if protocol not in self.__class__.AVAILABLE_PROTOCOLS:
            raise Exception("Invalid protocol %s" % protocol)
        self.protocol = protocol
        ifn = lambda x: int(x) if x is not None else None
        self.proxy_id = ifn(proxy_id)
        self._proxy_key = proxy_key
        

    def urlify(self):
        return "%s://%s:%s" % (self.protocol, self.address, self.port)

    def id(self):
        return self.proxy_id

    @property
    def proxy_key(self):
        if self._proxy_key is None and self.proxy_id is not None:
            self._proxy_key = "%s_%s" % ('p',self.proxy_id)
        return self._proxy_key
        
    @proxy_key.setter
    def proxy_key(self,pkey):
        self._proxy_key = pkey

    def to_dict(self,redis_format=False):
        obj_dict = {
            "address": self.address,
            "port":  str(self.port),
            "protocol": self.protocol,
        }

        if self.proxy_id is not None:
            obj_dict.update({'proxy_id': self.proxy_id})
        return obj_dict

class Detail(object):
    def proxy_object_id(self,object_or_id):
        if isinstance(object_or_id,int) or object_or_id is None:
            return object_or_id
        if isinstance(object_or_id, str):
            return int(object_or_id)
        return object_or_id.id()

    def __init__(self, active=False, load_time=60000, last_updated=None, last_active=DEFAULT_TIMESTAMP, last_used=DEFAULT_TIMESTAMP, bad_count=0, blacklisted=False, blacklisted_count=0, lifetime_good=0, lifetime_bad=0, proxy_id=None, queue_id=None, detail_id=None, queue_key=None, proxy_key=None, detail_key=None):
        self.active = active
        self.load_time = load_time
        self._last_active = parse_timestamp(last_active)
        self._last_used = parse_timestamp(last_used)
        self.bad_count = int(bad_count)
        self.blacklisted = blacklisted
        self.blacklisted_count = int(blacklisted_count)
        self.lifetime_good = int(lifetime_good)
        self.lifetime_bad = int(lifetime_bad)
        
        self.proxy_id = self.proxy_object_id(proxy_id)
        self.queue_id = self.proxy_object_id(queue_id)
        self._proxy_key = proxy_key
        self._queue_key = queue_key

        ifn = lambda x: int(x) if x is not None else None
        self.detail_id = ifn(detail_id)

    
    @property
    def proxy_key(self):
        if self.proxy_id is not None:
            self._proxy_key = "%s_%s" % ("p",self.proxy_id)
        return self._proxy_key
        
    
    @proxy_key.setter
    def proxy_key(self,pkey):
        self._proxy_key = pkey

    @property
    def queue_key(self):
        if self.queue_id is not None:
            self._queue_key = "%s_%s" % ('q',self.queue_id)
        return self._queue_key
            
    @queue_key.setter
    def queue_key(self,qkey):
        self._queue_key = qkey

    @property
    def detail_key(self):
        return "%s_%s_%s" % ('d',self.queue_key,self.proxy_key)



    def id(self):
        return self.detail_id

    @property
    def active(self):        
        return self._active
    
    @active.setter
    def active(self,val):
        self._active = parse_boolean(val)

    @property
    def blacklisted(self):
        return self._blacklisted
    
    @blacklisted.setter
    def blacklisted(self,val):
        self._blacklisted = parse_boolean(val)

    @property
    def last_active(self):
        return self._last_active

    @last_active.setter
    def last_active(self,val):
        self._last_active = parse_timestamp(val)

    @property
    def last_used(self):
        return self._last_used

    @last_used.setter
    def last_used(self,val):
        self._last_used = parse_timestamp(val)
            

    def to_dict(self,redis_format=False):
        obj_dict =  {
            "active": self.active,
            "load_time": self.load_time,
            "last_used": self.last_used,
            "last_active": self.last_active,
            "bad_count": self.bad_count,
            "blacklisted": self.blacklisted,
            "blacklisted_count": self.blacklisted_count,
            "lifetime_good": self.lifetime_good,
            "lifetime_bad": self.lifetime_bad, 
        }

        if redis_format:
            obj_dict['active'] = format_redis_boolean(self.active)
            obj_dict['blacklisted'] = format_redis_boolean(self.blacklisted)
            obj_dict['last_used'] =  format_redis_timestamp(self.last_used)
            obj_dict['last_active'] =format_redis_timestamp(self.last_active)
            obj_dict['queue_key'] = self.queue_key
            obj_dict['proxy_key'] = self.proxy_key

        if self.detail_id is not None:
            obj_dict.update({'detail_id': self.detail_id})

        if self.proxy_id is not None:
            obj_dict.update({'proxy_id': self.proxy_id})

        if self.queue_id is not None:
            obj_dict.update({'queue_id': self.queue_id})
        
        return obj_dict

 

    
    


class Queue(object):
    def __init__(self, domain, queue_id=None, queue_key=None):
        self.domain = domain
        ifn = lambda x: int(x) if x is not None else None
        self.queue_id = ifn(queue_id)
        self._queue_key = queue_key

    def id(self):
        return self.queue_id

    @property
    def queue_key(self):
        if self._queue_key is None and self.queue_id is not None:
            self._queue_key = "%s_%s" % (QUEUE_PREFIX,self.queue_id)
        return self._queue_key
            
    @queue_key.setter
    def proxy_key(self,qkey):
        self._queue_key = qkey
    
    def to_dict(self, redis_format=False):
        obj_dict = {
            "domain": self.domain,
        }

        if(self.queue_id is not None):
            obj_dict.update({"queue_id": self.queue_id})
        
        return obj_dict

"""
   def decrement_bad_count(self):
        if self.bad_count > 0:
            self.bad_count -= 1
            self.decrement_blacklisted_count()
    
    def increment_bad_count(self):
        self.bad_count += 1
        self.lifetime_bad += 1
        if self.bad_count > BLACKLIST_THRESHOLD:
            self.blacklisted = True
            self.blacklisted_count += 1
            self.bad_count = 0

    def decrement_blacklist_count(self):
        if DECREMENT_BLACKLIST and self.blacklisted_count > 0:
            self.blacklisted_count -= 1
"""

class ProxyObject(Proxy):
    def __init__(self,detail,storage_manager,rdq):
        self.detail = detail
        self.storage_mgr = storage_manager
        self.proxy = self.storage_mgr.redis_mgr.get_proxy(detail.proxy_key)
        self._dispatch_time = None
        self.rdq = rdq

        super().__init__(self.proxy.address, self.proxy.port,
                         self.proxy.protocol, self.proxy.proxy_id)

    def dispatch(self):
        self._dispatch_time = datetime.utcnow()

    def callback(self, success):
        logging.info("callback=%s for proxy %s" % (success,self.urlify()))
        if self._dispatch_time is None:
            raise Exception("Proxy not properly dispatched prior to callback.")

        requeue = True
        self.detail.last_used = datetime.utcnow()

        

        if success is None:
            requeue = False

        

        elif success:
            logging.info("proxy.callback(success=True)")
            load_time_delta = datetime.utcnow() - self._dispatch_time
            self.detail.load_time = load_time_delta.seconds
            self.detail.active = True
            self.detail.last_active = datetime.utcnow()
            #self.detail.decrement_bad_count()
            self.detail.lifetime_good += 1
            if DECREMENT_BLACKLIST:
                if self.detail.blacklisted_count > 0:
                    self.detail.blacklisted_count -= 1
            
        else:
            logging.info("proxy.callback(success=False)")
            self.detail.bad_count += 1
            self.detail.lifetime_bad += 1
            if self.detail.bad_count > BLACKLIST_THRESHOLD:

                self.detail.blacklisted = True
                self.detail.active = False
                self.detail.blacklisted_count += 1
        
        self.storage_mgr.redis_mgr.update_detail(self.detail)
        


        self.detail = self.storage_mgr.redis_mgr.get_detail(self.detail.detail_key)


        logging.info("""
        ----------|---------------------------------------------------------------------|
        ----------|  proxy address/port     : %s  
        ----------|  successful requests    : %s" 
        ----------|  unsuccessful requests  : %s" 
        ----------|  last active            : %s" 
        ----------|  last used              : %s" 
        ----------|---------------------------------------------------------------------| 
        """ % (self.urlify(), self.detail.lifetime_good, self.detail.lifetime_bad, self.detail.last_active, self.detail.last_used))






        if requeue:
            self.rdq.enqueue(self.detail)

        self._dispatch_time = None




    def to_dict(self,redis_format=False):
        return self.detail.to_dict(redis_format)
            

        
