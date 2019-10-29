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


SEED_QUEUE_ID = configuration.app_config['seed_queue']['value']
AGGREGATE_QUEUE_ID = configuration.app_config['aggregate_queue']['value']
LIMIT_ACTIVE = configuration.app_config['active_proxies_per_queue']['value']
LIMIT_INACTIVE = configuration.app_config['inactive_proxies_per_queue']['value']
LIMIT_SEED = configuration.app_config['seed_proxies_per_queue']['value']


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

    def do_query(self, query, params=None):
        cursor = self.cursor()
        cursor.execute(query,params)
        data = cursor.fetchall()
        cursor.close()
        return data





class Redis(redis.Redis):
    def __init__(self,*args,**kwargs):
        super().__init__(decode_responses=True,*args,**kwargs)

class RedisManager(object):
    def __init__(self):
        logging.info("redis manager init")
        self.redis = Redis(**configuration.redis_config)
        self.dbh = PostgresManager()

            
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
        
        query = "SELECT * FROM queues;"
        queues = {r['queue_id']: Queue(**r) for r in self.dbh.do_query(query)}

        queues[SEED_QUEUE_ID] = Queue(queue_id=SEED_QUEUE_ID, domain="SEED_QUEUE")    
        queues[AGGREGATE_QUEUE_ID] = Queue(queue_id=AGGREGATE_QUEUE_ID, domain="AGGREGATE_QUEUE")

        for queue_object in queues.values():
            self.register_queue(queue_object)
        return queues

    def get_queues_from_cache(self):
        return self.redis.keys('q_*')
    

    def get_seed_queue(self):
        pass

    def get_seed_count(self):
        query = "SELECT COUNT(*) as detail_count FROM details where queue_id=%(queue_id)s;"
        params = {'queue_id': SEED_QUEUE_ID}
        return self.dbh.do_query(query,params)[0]['detail_count']
        


    def init_seeds(self):
        return []
        




    def get_proxies_from_db(self):
        seeds = []
        seed_count = self.get_seed_count()
        if(seed_count == 0):
            seeds = self.init_seeds()


        else:
            seed_proxies_query = """
                SELECT * FROM details
                WHERE queue_id = %(seed_queue_id)s
                AND active = %(active)s
                ORDER BY last_used ASC
                LIMIT %(limit)s;
            """
            paramms1 = {"seed_queue_id": SEED_QUEUE_ID, "active": True, "limit":LIMIT_ACTIVE}
            params2 = {"seed_queue_id": SEED_QUEUE_ID, "active": False, "limit":LIMIT_INACTIVE}
            res1 = self.dbh.do_query(seed_proxies_query, seed_query_params1)
            res2 = self.dbh.do_query(seed_proxies_query, seed_query_params2)
            seeds = [Detail(**r) for r in res1+res2]


        





    def sync_from_db(self):
        self.redis.flushall()
        self.redis.save()
        self.redis.set('temp_queue_id',0)
        self.redis.set('temp_proxy_id',0)
        self.redis.set('temp_detail_id',0)

        self.get_queues_from_db()
        self.get_proxies_from_db()

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
