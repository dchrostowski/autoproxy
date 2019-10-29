import redis
import psycopg2
import sys
import os
import logging
import time

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

from psycopg2.extras import DictCursor
from IPython import embed
from proxy_objects import Proxy, Detail, Queue

from autoproxy_config.config import configuration

class PostgresManager(object):
    def __init__(self):
        self.connect_params = configuration.db_config
        self.connect_params.update({'cursor_factory':DictCursor})

    def new_connection(self):
        conn = psycopg2.connect(**self.connect_params)
        conn.set_session(autocommit=True)
        return conn
    
    def cursor(self):
        return self.new_connection().cursor()


class Redis(redis.Redis):
    def __init__(self,*args,**kwargs):
        super().__init__(decode_responses=True,*args,**kwargs)

class RedisManager(object):
    def __init__(self):
        logging.info("redis manager init")
        self.redis = Redis(**configuration.redis_config)
        self.postgres_manager = PostgresManager()

            
        while self.redis.get('init') is None:
            lock = self.redis.lock('syncing')
            if lock.acquire(blocking=True, blocking_timeout=1):
                if self.redis.get('init') is None:
                    self.sync_from_db()
                    self.redis.set("init",1)
                    try:
                        lock.release()
                    except Exception:
                        pass

    def get_queues_from_db(self):
        logging.info("fetching queues")
        data = {}
        cursor = self.postgres_manager.cursor()
        cursor.execute("select * from queues")
        queues = {r.queue_id: Queue(**r) for r in cursor.fetchall()}
        cursor.close()

        sqid = configuration.app_config['seed_queue']['value']
        aqid = configuration.app_config['aggregate_queue']['value']

        queues[sqid] = Queue(queue_id=sqid, domain="SEED_QUEUE")    
        queues[aqid] = Queue(queue_id=aqid, domain="AGGREGATE_QUEUE")

        for queue_object in queues.values():
            self.register_queue(queue_object)
        return queues

    def get_queues_from_cache(self):
        return self.redis.keys('q_*')


    def get_proxies_from_db(self):
        logging.info("fetching proxies")





    def sync_from_db(self):
        self.redis.flushall()
        self.redis.save()
        self.redis.set('temp_queue_id',0)
        self.redis.set('temp_proxy_id',0)
        self.redis.set('temp_detail_id',0)

        self.get_queues_from_db()
        self.get_details_from_db()

        """    
        proxies = { p['proxy_id']: Proxy(**p) for p in data['proxies'] }
        queues= { q['queue_id']: Queue(**q) for q in data['queues'] }
        details = { d['detail_id']: Detail(**q) for d in data['details'] }
        """
        proxies = data['proxies']
        queues = data['queues']
        #details = data['details']

        




        
        #self.save_to_cache(proxy_object_instances, next_ids)
    

    def register_proxy(self, proxy):
        logging.info('register proxy')
        redis_id = None
        if proxy.proxy_id is None:
            self.redis.hmset("tp_%s" % self.redis.incr('temp_proxy_id'), proxy.to_dict())
        else:
            self.redis.hmset('p_%s' % proxy.proxy_id, proxy.to_dict())


    def register_queue(self,queue):
        logging.info("register_queue")
        redis_id = None
        if queue.queue_id is None:
            self.redis.hmset("tq_%s" % self.redis.incr('temp_queue_id'), queue.to_dict())
        else:
            self.redis.hmset('q_%s' % queue.queue_id, queue.to_dict())
        


    def save_to_cache(self,pqd_objects, next_ids):
        pass




        

            




redis_manager = RedisManager()
cache = redis_manager.redis
