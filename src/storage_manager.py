import redis
import psycopg2
import sys
import os
import logging
import time
import json
from functools import wraps
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

# decorator for RedisManager methods
def block_if_syncing(func):
    @wraps(func)
    def wrapper(self,*args,**kwargs):
        while self.redis.get('syncing') is not None:
            time.sleep(1)
        return(func(self,*args,**kwargs))
    return wrapper


class PostgresManager(object):
    def __init__(self):
        connect_params = configuration.db_config
        connect_params.update({'cursor_factory':DictCursor})
        self.connect_params = connect_params

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
            return data
        except Exception:
            pass
        cursor.close()

    def insert_object(self,obj,table,cursor=None):
        table_name = sql.Identifier(table)
        column_sql = sql.SQL(', ').join(map(sql.Identifier, obj.to_dict().keys()))
        placeholder_sql = sql.SQL(', ').join(map(sql.Placeholder,obj.to_dict()))
        
        insert = sql.SQL('INSERT INTO {0} ({1}) VALUES ({2})').format(table_name,column_sql,placeholder_sql)

        insert_fn = cursor
        if insert_fn is None:
            insert_fn = self.do_query
        
        insert_fn(insert,obj.to_dict())


    def insert_detail(self,detail, cursor=None):
        self.insert_object(detail,'details')

    def insert_queue(self,queue, cursor=None):
        self.insert_object(queue,'queues')

    def insert_proxy(self,proxy,cursor=None):
        self.insert_object(proxy,'proxies')


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
        active =  [Detail(**d) for d in self.do_query("SELECT * FROM details WHERE queue_id=%(seed_queue_id)s",params)]
        inactive = [Detail(**d) for d in self.do_query("SELECT * FROM details WHERE queue_id=%(seed_queue_id)s",params)]



    def init_seed_queues(self):
        if(SEED_QUEUE_ID == AGGREGATE_QUEUE_ID):
            raise Exception("aggregate_queue and seed_queue cannot share the same id.  Check app_config.json")
        
        seed_queue = Queue(domain=SEED_QUEUE_DOMAIN,queue_id=SEED_QUEUE_ID)
        agg_queue = Queue(domain=AGGREGATE_QUEUE_DOMAIN, queue_id=AGGREGATE_QUEUE_ID)

        query = "SELECT queue_id from queues WHERE domain = %(domain)s"
        db_seed = self.do_query(query, {'domain':SEED_QUEUE_DOMAIN})
        db_agg = self.do_query(query, {'domain': AGGREGATE_QUEUE_DOMAIN})
        
        if len(db_seed) == 0:
            self.insert_queue(seed_queue)
        elif db_seed[0]['queue_id'] != SEED_QUEUE_ID:
            raise Exception("seed_queue id mismatch. seed_queue should be set to %s  Check app_config.json" % db_seed[0]['queue_id'])
        
        if len(db_agg) == 0:
            self.insert_queue(agg_queue)
        elif(db_agg[0]['queue_id'] != AGGREGATE_QUEUE_ID):
            raise Exception("aggregate queue_id mismatch.  aggregate_queue should be set to %s  Check app_config.json" % db_agg[0]['queue_id'])
        

    def get_queues(self):
        self.init_seed_queues()
        queues = [Queue(**r) for r in self.do_query("SELECT * FROM queues;")]
        return queues

class Redis(redis.Redis):
    def __init__(self,*args,**kwargs):
        super().__init__(decode_responses=True,*args,**kwargs)

class RedisManager(object):
    def __init__(self):
        self.redis = Redis(**configuration.redis_config)
        self.dbh = PostgresManager()

        if len(self.redis.keys()) == 0:
            lock = self.redis.lock('syncing')
            if lock.acquire(blocking=True, blocking_timeout=0):
                self.sync_from_db()
                lock.release()

    def sync_from_db(self):
        self.redis.set(QUEUE_PREFIX,0)
        self.redis.set(PROXY_PREFIX,0)
        self.redis.set(DETAIL_PREFIX,0)

        queues = self.dbh.get_queues()
        for q in queues:
            self.register_queue(q)
        
        seed_details = self.dbh.get_seed_details()
    
    
    def register_object(self,key,obj):
        redis_key = key
        if obj.id() is None:
            redis_key += 't_%s' % self.redis.incr(key)
        else:
            redis_key += '_%s' % obj.id()
        
        self.redis.hmset(redis_key,obj.to_dict())

    
    def register_queue(self,queue):
        self.register_object(QUEUE_PREFIX,queue)
    
    def register_detail(self,detail):
        self.register_object(DETAIL_PREFIX,detail)
    
    @block_if_syncing
    def increment_foo(self):
        print(self.redis.incr('foo'))

