import redis
import psycopg2
import sys
import os
import logging
import time
import json

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

from psycopg2.extras import DictCursor
from psycopg2 import sql
from IPython import embed
from proxy_objects import Proxy, Detail, Queue

from autoproxy_config.config import configuration


SEED_QUEUE_ID = configuration.app_config['seed_queue']['value']
AGGREGATE_QUEUE_ID = configuration.app_config['aggregate_queue']['value']
LIMIT_ACTIVE = configuration.app_config['active_proxies_per_queue']['value']
LIMIT_INACTIVE = configuration.app_config['inactive_proxies_per_queue']['value']
LIMIT_SEED = configuration.app_config['seed_proxies_per_queue']['value']
SEED_QUEUE_DOMAIN = 'RESERVED_SEED_QUEUE'
AGGREGATE_QUEUE_DOMAIN = 'RESERVED_AGGREGATE_QUEUE'
QUEUE_PREFIX = configuration.app_config['redis_queue_char']['value']
PROXY_PREFIX = configuration.app_config['redis_proxy_char']['value']
DETAIL_PREFIX = configuration.app_config['redis_detail_char']['value']


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
        try:
            data = cursor.fetchall()
        except Exception:
            pass
        cursor.close()
        return data
    
    def db_columns_values(self,obj):
        obj_dict = obj.to_dict()
        obj_keys = []
        obj_vals = []
        for k,v in obj_dict.items():
            obj_keys.append(k)
            obj_vals.append(v)

        columns_str = sql.SQL(', ').join(map(sql.Identifier, obj_keys))
        values_str = sql.SQL(', ').join([sql.Placeholder(name=k) for k in obj_keys])

        return {'columns': columns_str, 'values': values_str}
        

    def insert_queue(self,queue, cursor=None):
        cv = self.db_columns_values(queue)
        insert = sql.SQL("INSERT INTO queues ({0}) VALUES ({1})").format(cv['columns'], cv['values'])
        
        fn = self.do_query
        if cursor is not None:
            fn = cursor
        fn(insert,queue.to_dict())
        
        
        
    
    def init_seed_queues(self):
        params = {'seed':SEED_QUEUE_ID,'agg':AGGREGATE_QUEUE_ID}
        if(SEED_QUEUE_ID == AGGREGATE_QUEUE_ID):
            raise Exception("aggregate_queue and seed_queue cannot share the same id.  Check app_config.json")
        query = "SELECT queue_id from queues WHERE domain = %(domain)s"

        seed_res = self.do_query(query, {'domain':SEED_QUEUE_DOMAIN})
        agg_res = self.do_query(query, {'domain': AGGREGATE_QUEUE_DOMAIN})
        
        
        if len(seed_res) < 1:
            self.insert_queue(Queue(domain=SEED_QUEUE_DOMAIN,queue_id=SEED_QUEUE_ID))
        elif seed_res[0]['queue_id'] != SEED_QUEUE_ID:
            raise Exception("seed_queue id mismatch. seed_queue should be set to %s  Check app_config.json" % seed_res[0]['queue_id'])
        if(len(agg_res) < 1):
            self.insert_queue(Queue(domain=AGGREGATE_QUEUE_DOMAIN, queue_id=AGGREGATE_QUEUE_ID))
        elif(agg_res[0]['queue_id'] != AGGREGATE_QUEUE_ID):
            raise Exception("aggregate queue_id mismatch.  aggregate_queue should be set to %s  Check app_config.json" % agg_res[0]['queue_id'])
        

    def get_queues(self):
        self.init_seed_queues()
        queues = [Queue(**r) for r in self.do_query("SELECT * FROM queues;")]
        return queues

    def insert_detail(self,detail, cursor=None):
        cv = self.db_columns_values(detail)
        insert = sql.SQL('INSERT INTO details ({0}) VALUES ({1})').format(cv['columns'], cv['values'])
        if cursor is None:
            self.do_query(insert,detail.to_dict())
        else:
            cursor.execute(insert,detail.to_dict())


    def init_seed_details(self):
        seed_count = self.do_query("SELECT COUNT(*) as c FROM details WHERE queue_id=%(queue_id)s", {'queue_id':SEED_QUEUE_ID})[0]['c']
        if seed_count == 0:
            seed_details = [Detail(proxy=p['proxy_id']) for p in self.do_query("SELECT proxy_id FROM proxies")]
            cursor = self.cursor()
            for sd in seed_details:
                self.insert_detail(sd,cursor)
            cursor.close()
        
    def get_seed_details(self):
        self.init_seed_details()
        params = {'seed_queue_id': SEED_QUEUE_ID}
        return [Detail(**d) for d in self.do_query("SELECT * FROM details WHERE queue_id=%(seed_queue_id)s",params)]






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

    def sync_from_db(self):
        self.redis.flushall()
        self.redis.save()
        self.redis.set('temp_queue_id',0)
        self.redis.set('temp_proxy_id',0)
        self.redis.set('temp_detail_id',0)

        queues = self.dbh.get_queues()
        details = self.dbh.get_seed_details()

        

    def register_proxy(self, proxy):
        logging.info('register proxy')
        redis_id = None
        if proxy.proxy_id is None:
            self.redis.hmset("tp_%s" % self.redis.incr('temp_proxy_id'), proxy.to_dict())
        else:
            self.redis.hmset('p_%s' % proxy.proxy_id, proxy.to_dict())

    def register_proxy_object(self,prefix_char, proxy_object):
        print(proxy_object.__class__)


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
