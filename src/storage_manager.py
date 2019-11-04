import redis
import psycopg2
import sys
import os
import logging
import time
import json
import re
from functools import wraps
from copy import deepcopy
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

from psycopg2.extras import DictCursor
from psycopg2 import sql
from IPython import embed
from proxy_objects import Proxy, Detail, Queue
from util import parse_domain

from autoproxy_config.config import configuration


SEED_QUEUE_ID = configuration.app_config['seed_queue']['value']
AGGREGATE_QUEUE_ID = configuration.app_config['aggregate_queue']['value']
LIMIT_ACTIVE = configuration.app_config['active_proxies_per_queue']['value']
LIMIT_INACTIVE = configuration.app_config['inactive_proxies_per_queue']['value']
LIMIT_SEED = configuration.app_config['seed_proxies_per_queue']['value']
SEED_QUEUE_DOMAIN = parse_domain(configuration.app_config['designated_endpoint']['value'])
AGGREGATE_QUEUE_DOMAIN = 'RESERVED_AGGREGATE_QUEUE'
QUEUE_PREFIX = configuration.app_config['redis_queue_char']['value']
PROXY_PREFIX = configuration.app_config['redis_proxy_char']['value']
DETAIL_PREFIX = configuration.app_config['redis_detail_char']['value']
ACTIVE_LIMIT = configuration.app_config['active_proxies_per_queue']['value']
INACTIVE_LIMIT = configuration.app_config['inactive_proxies_per_queue']['value']
SEED_LIMIT = configuration.app_config['seed_proxies_per_queue']['value']
TEMP_ID_COUNTER = 'temp_id_counter'

# decorator for RedisManager methods
def block_if_syncing(func):
    @wraps(func)
    def wrapper(self,*args,**kwargs):
        while self.is_syncing() and not self.is_sync_client():
            logging.info('awaiting sync...')
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

    def insert_object(self,obj,table,returning, cursor=None):
        table_name = sql.Identifier(table)
        column_sql = sql.SQL(', ').join(map(sql.Identifier, obj.to_dict().keys()))
        placeholder_sql = sql.SQL(', ').join(map(sql.Placeholder,obj.to_dict()))
        returning = sql.Identifier(returning)
        
        insert = sql.SQL('INSERT INTO {0} ({1}) VALUES ({2}) RETURNING {3}').format(table_name,column_sql,placeholder_sql, returning)


        if cursor is not None:
            cursor.execute(insert,obj.to_dict())
        else:
            self.do_query(insert,obj.to_dict())



    def insert_detail(self,detail, cursor=None):
        self.insert_object(detail,'details', 'detail_id',cursor)

    def insert_queue(self,queue, cursor=None):
        self.insert_object(queue,'queues','queue_id', cursor)

    def insert_proxy(self,proxy,cursor=None):
        self.insert_object(proxy,'proxies','proxy_id',cursor)

    def init_seed_details(self):
        seed_count = self.do_query("SELECT COUNT(*) as c FROM details WHERE queue_id=%(queue_id)s", {'queue_id':SEED_QUEUE_ID})[0]['c']
        logging.info("initializing seed proxies")
        cursor = self.cursor()
        if seed_count == 0:
            seed_details = [Detail(proxy_id=p['proxy_id'], queue_id=SEED_QUEUE_ID) for p in self.do_query("SELECT proxy_id FROM proxies")]
            for sd in seed_details:
                self.insert_detail(sd,cursor)
        
        query = """
        BEGIN;
        LOCK TABLE details IN EXCLUSIVE MODE;
        SELECT setval('details_detail_id_seq', COALESCE((SELECT MAX(detail_id)+1 FROM details),1), false);
        COMMIT;
        """
        
        cursor.execute(query)
        cursor.close()
        logging.info("done initializing seeds")
        
    def get_seed_details(self):
        self.init_seed_details()
        params = {'seed_queue_id': SEED_QUEUE_ID}
        query= """
            SELECT * FROM details 
            WHERE queue_id=%(queue_id)s
            AND active=%(active)s
            ORDER BY last_used ASC
            LIMIT %(limit)s;
            """
        a_params = {"queue_id":SEED_QUEUE_ID, "active":True,"limit": ACTIVE_LIMIT}
        ia_params = {"queue_id":SEED_QUEUE_ID, "active":False,"limit": INACTIVE_LIMIT}
        active =  [Detail(**d) for d in self.do_query(query,a_params)]
        inactive = [Detail(**d) for d in self.do_query(query,ia_params)]
        
        return active + inactive




    def init_seed_queues(self):
        logging.info("Initializing queues...")
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

        cursor = self.cursor()
        query = """
        BEGIN;
        LOCK TABLE queues IN EXCLUSIVE MODE;
        SELECT setval('queues_queue_id_seq', COALESCE((SELECT MAX(queue_id)+1 FROM queues),1), false);
        COMMIT;
        """
        cursor.execute(query)
        cursor.close()
        logging.info("Finished initializing queue.")
        


    def get_queues(self):
        self.init_seed_queues()
        return [Queue(**r) for r in self.do_query("SELECT * FROM queues;")]
        

    def get_proxies(self):
        return [Proxy(**p) for p in self.do_query("SELECT * FROM proxies")]

    def get_detail_by_queue_and_proxy(self,queue_id,proxy_id):
        query = "SELECT * FROM details WHERE proxy_id=%(proxy_id)s AND queue_id=%(queue_id)s"
        params = {'queue_id': queue_id, 'proxy_id':proxy_id}
        cursor = self.cursor()
        cursor.execute(query,params)
        detail_data = cursor.fetchone()
        if detail_data is None:
            cursor.close()
            return None
        detail = Detail(**detail_data)
        cursor.close()
        return detail
        

class Redis(redis.Redis):
    def __init__(self,*args,**kwargs):
        super().__init__(decode_responses=True,*args,**kwargs)

class RedisDetailQueueEmpty(Exception):
    pass
class RedisDetailQueueInvalid(Exception):
    pass

class RedisDetailQueue(object):
    def __init__(self,queue_key):
        self.redis = Redis(**configuration.redis_config)
        self.queue_key = queue_key
        self.redis_key = 'redis_detail_queue_%s' % queue_key
    
    def is_empty(self):
        if not self.redis.exists(self.redis_key):
            return True
        elif self.redis.llen(self.redis_key) == 0:
            return True
        else:
            return False

    def enqueue(self,detail):

        detail_key = detail.detail_key
        detail_queue_key = self.redis.hget(detail_key,'queue_key')

        if detail_queue_key != self.queue_key:
            raise RedisDetailQueueInvalid("No such queue key for detail")
        
        self.redis.rpush(self.redis_key,detail_key)

    def dequeue(self):
        if self.is_empty():
            raise RedisDetailQueueEmpty("No proxies available for queue id %s" % self.queue_id)
        detail = Detail(**self.redis.hgetall(self.redis.lpop(self.redis_key)))
        self.enqueue(detail)
        return detail

    def length(self):
        return self.redis.llen(self.redis_key)

    def clear(self):
        self.redis.delete(self.redis_key)
    

class RedisManager(object):
    def __init__(self):
        self.redis = Redis(**configuration.redis_config)
        self.dbh = PostgresManager()

        if len(self.redis.keys()) == 0:
            lock = self.redis.lock('syncing')
            if lock.acquire(blocking=True, blocking_timeout=0):
                self.redis.client_setname('syncer')
                self.sync_from_db()
                self.redis.client_setname('')
                lock.release()

    def is_sync_client(self):
        return self.redis.client_getname() == 'syncer'

    def is_syncing(self):
        return self.redis.get('syncing') is not None

    @block_if_syncing
    def sync_from_db(self):
        self.redis.set("%s_%s" % (TEMP_ID_COUNTER, QUEUE_PREFIX),0)
        self.redis.set("%s_%s" % (TEMP_ID_COUNTER, PROXY_PREFIX),0)
        self.redis.set("%s_%s" % (TEMP_ID_COUNTER, DETAIL_PREFIX),0)
        self.redis.delete('detail_ids')

        queues = self.dbh.get_queues()
        for q in queues:
            self.register_queue(q)

        proxies = self.dbh.get_proxies()
        for p in proxies:
            self.register_proxy(p)
        
        seed_details = self.dbh.get_seed_details()
        logging.info("got details")

        for d in seed_details:
            #d.queue_key = "%s_%s" % (QUEUE_PREFIX,SEED_QUEUE_ID)
            #d.proxy_key = "%s_%s" % (PROXY_PREFIX,PROXY_QUEUE_ID
            self.register_detail(d)
    
    @block_if_syncing
    def register_object(self,key,obj):
        redis_key = key
        if obj.id() is None:
            temp_counter_key = "%s_%s" % (TEMP_ID_COUNTER, key)
            redis_key += 't_%s' % self.redis.incr(temp_counter_key)
        else:
            redis_key += '_%s' % obj.id()
        
        self.redis.hmset(redis_key,obj.to_dict())
        return redis_key

    def register_queue(self,queue):
        logging.info("registering queue")
        queue_key = self.register_object(QUEUE_PREFIX,queue)
        self.redis.hmset(queue_key, {'queue_key': queue_key})
        
        return Queue(**self.redis.hgetall(queue_key))

    def register_proxy(self,proxy):
        logging.info("registering proxy")
        proxy_key = self.register_object(PROXY_PREFIX,proxy)
        self.redis.hmset(proxy_key, {'proxy_key': proxy_key})


        return Proxy(**self.redis.hgetall(proxy_key))
    
    @block_if_syncing
    def register_detail(self,detail):
        logging.info("registering detail")
        
        if detail.proxy_key is None or detail.queue_key is None:
            rdq1 = RedisDetailQueue(queue_key='q_1')
            raise Exception('detail object must have a proxy and queue key')
        if not self.redis.exists(detail.proxy_key) or not self.redis.exists(detail.queue_key):
            raise Exception("Unable to locate queue or proxy for detail")

        detail_key = detail.detail_key
        
        if self.redis.exists(detail.detail_key):
            logging.warn("Detail already exists")
            return Detail(**self.redis.hgetall(detail_key))
        else:
            self.redis.hmset(detail_key, detail.to_dict())
        
        relational_keys = {'proxy_key': detail.proxy_key, 'queue_key': detail.queue_key}
        self.redis.hmset(detail_key, relational_keys)
        rdq = RedisDetailQueue(detail.queue_key)
        rdq.enqueue(detail)

        return Detail(**self.redis.hgetall(detail_key))

    @block_if_syncing
    def get_detail(self,redis_detail_key):
        return Detail(**self.redis.hgetall(redis_detail_key))

    @block_if_syncing
    def get_all_queues(self):
        return [Queue(**self.redis.hgetall(q)) for q in self.redis.keys('q*')]

    @block_if_syncing
    def get_all_temp_id_queues(self):
        return [Queue(**self.redis.hgetall(q)) for q in self.redis.keys("qt*")]


class StorageManager(object):
    def __init__(self):
        self.redis_mgr = RedisManager()
        self.db_mgr = PostgresManager()

    def create_queue(self,url):
        logging.info("creating queue for %s" % url)
        domain = parse_domain(url)
        all_queues_by_domain = {queue.domain: queue for queue in self.redis_mgr.get_all_queues()}
        if domain in all_queues_by_domain:
            logging.warn("Trying to create a queue that already exists.")
            return all_queues_by_domain[domain]
        
        return self.redis_mgr.register_queue(Queue(domain=domain))

    def create_proxy(self, address, port, protocol):
        proxy_keys = self.redis_mgr.redis.keys('p*')
        for pkey in proxy_keys:
            if self.redis_mgr.redis.hget(pkey,'address') == address and self.redis_mgr.redis.hget(pkey,'port'):
                logging.warn("Trying to create a proxy that already exists")
                return Proxy(**self.redis_mgr.redis.hgetall(pkey))

        proxy = Proxy(address=address,port=port,protocol=protocol)
        proxy = self.redis_mgr.register_proxy(proxy)
        proxy_key = proxy.proxy_key
        queue_key = "%s_%s" % (QUEUE_PREFIX,SEED_QUEUE_ID)
        detail = Detail(proxy_key=proxy_key,queue_id=SEED_QUEUE_ID,queue_key=queue_key)
        
        
        self.redis_mgr.register_detail(detail)
        
        return proxy

    def clone_detail(self,detail,new_queue):
        new_queue_key = new_queue.queue_key
        
        if detail.queue_id != SEED_QUEUE_ID:
            raise Exception("can only clone details from seed queue")
        if not self.redis_mgr.redis.exists(new_queue_key):
            raise Exception("Invalid queue key while cloning detail")
        
        new_queue_id = self.redis_mgr.redis.hget(new_queue_key,'queue_id')
        proxy_id = detail.proxy_id
        proxy_key = detail.proxy_key
        print("new quueue key:" + new_queue_key)
        cloned = Detail(proxy_id=proxy_id,queue_id=new_queue_id,queue_key=new_queue_key, proxy_key=proxy_key)
        print("cloned detail key")
        print(cloned.detail_key)
        
        
        new_detail_key = cloned.detail_key

        if self.redis_mgr.redis.exists(new_detail_key):
            logging.warn("trying to clone a detail into a queue where it already exists.")
            return Detail(**self.redis_mgr.redis.hgetall(new_detail_key))

        if new_queue_id is not None and proxy_id is not None:
            db_detail = self.db_mgr.get_detail_by_queue_and_proxy(new_queue_id,proxy_id)
            if db_detail is not None:
                logging.warn("Attempting to clone a detail that already exists")
                return self.redis_mgr.register_detail(db_detail)

        return self.redis_mgr.register_detail(cloned)


    def sync_to_db(self):
        new_queues = [Queue(**self.redis_mgr.redis.hgetall(q)) for q in self.redis_mgr.redis.keys("qt_*")]
        new_proxies = [Proxy(**self.redis_mgr.redis.hgetall(p)) for p in self.redis_mgr.redis.keys("pt_*")]
        new_detail_keys = set(self.redis_mgr.redis.keys('d_qt*') + self.redis_mgr.redis.keys('d_*pt*'))
        new_details = [Detail(**self.redis_mgr.redis.hgetall(d)) for d in list(new_detail_keys)]

        cursor = self.db_mgr.cursor()

        queue_keys_to_id = {}
        proxy_keys_to_id = {}
        for q in new_queues:
            self.db_mgr.insert_queue(q,cursor)
            queue_id = cursor.fetchone()[0]
            queue_keys_to_id[q.queue_key] = queue_id

        for p in new_proxies:
            self.db_mgr.insert_proxy(p,cursor)
            proxy_id = cursor.fetchone()[0]
            proxy_keys_to_id[p.proxy_key] = proxy_id

        for d in new_details:
            if d.proxy_id is None:
                d.proxy_id = proxy_keys_to_id[d.proxy_key]
            if d.queue_id is None:
                d.queue_id = queue_keys_to_id[d.queue_key]
            self.db_mgr.insert_detail(d,cursor)
            
        cursor.close()
        logging.info("synced redis cache to database, resetting cache.")
        self.redis_mgr.redis.flushall()

        


        
        
        


