import redis
import psycopg2
import sys
import os

import time
import json
import re
from functools import wraps
from copy import deepcopy
from datetime import datetime, timedelta
import traceback

from psycopg2.extras import DictCursor
from psycopg2 import sql
from scrapy_autoproxy.proxy_objects import Proxy, Detail, Queue
from scrapy_autoproxy.util import parse_domain
import logging
logger = logging.getLogger(__name__)

from scrapy_autoproxy.config import configuration
app_config = lambda config_val: configuration.app_config[config_val]['value']

SEED_QUEUE_ID = app_config('seed_queue')
AGGREGATE_QUEUE_ID = app_config('aggregate_queue')
LIMIT_ACTIVE = app_config('active_proxies_per_queue')
LIMIT_INACTIVE = app_config('inactive_proxies_per_queue')

SEED_QUEUE_DOMAIN = parse_domain(app_config('designated_endpoint'))
AGGREGATE_QUEUE_DOMAIN = 'RESERVED_AGGREGATE_QUEUE'
ACTIVE_LIMIT = app_config('active_proxies_per_queue')
INACTIVE_LIMIT = app_config('inactive_proxies_per_queue')
TEMP_ID_COUNTER = 'temp_id_counter'

BLACKLIST_THRESHOLD = app_config('blacklist_threshold')
MAX_BLACKLIST_COUNT = app_config('max_blacklist_count')
BLACKLIST_TIME = app_config('blacklist_time')
MAX_DB_CONNECT_ATTEMPTS = app_config('max_db_connect_attempts')
DB_CONNECT_ATTEMPT_INTERVAL = app_config("db_connect_attempt_interval")
PROXY_INTERVAL = app_config('proxy_interval')
LAST_USED_CUTOFF = datetime.utcnow() - timedelta(seconds=PROXY_INTERVAL)
NEW_DETAILS_SET_KEY = 'new_details'
CHANGED_DETAILS_SET_KEY = 'changed_details'
INITIAL_SEED_COUNT = app_config('initial_seed_count')
MIN_QUEUE_SIZE = app_config('min_queue_size')
NEW_QUEUE_PROXY_IDS_PREFIX = 'new_proxy_ids_'

import logging
logger = logging.getLogger(__name__)



class DetailExistsException(Exception):
    pass


# decorator for RedisManager methods
def block_if_syncing(func):
    @wraps(func)
    def wrapper(self,*args,**kwargs):
        while self.is_syncing() and not self.is_sync_client():
            logging.info("awaiting sync")
            time.sleep(5)
        return(func(self,*args,**kwargs))
    return wrapper


# To do - acquire queue sync lock

def queue_lock(func):
    @wraps(func)
    def wrapper(self,*args,**kwargs):
        redis = Redis(**configuration.redis_config)
        queue = kwargs.get('queue',None)
        if queue is None:
            raise Exception("queue_lock function must have a queue kwrargs")
        lock_key = 'syncing_%s' % queue.domain
        lock = redis.lock(lock_key)
        if lock.acquire(blocking=True,blocking_timeout=0):

            func(self,*args,**kwargs)
            lock.release()
        
        else:
            while redis.get(lock_key) is not None:

                time.sleep(5)
        return
        

    return wrapper


    

class PostgresManager(object):
    def __init__(self):
        connect_params = configuration.db_config
        connect_params.update({'cursor_factory':DictCursor})
        self.connect_params = connect_params
        self.connect_attempts = 0

    def new_connection(self):
        if self.connect_attempts < MAX_DB_CONNECT_ATTEMPTS:
            try:
                conn = psycopg2.connect(**self.connect_params)
                conn.set_session(autocommit=True)
            except Exception as e:
                self.connect_attempts +=1


                time.sleep(DB_CONNECT_ATTEMPT_INTERVAL)
                return self.new_connection()

            return conn
        else:
            raise Exception("Failed to connect to the database.")
    
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

    def update_detail(self,obj,cursor=None):
        table_name = sql.Identifier('details')
        obj_dict = obj.to_dict()
        where_sql = sql.SQL("{0}={1}").format(sql.Identifier('detail_id'),sql.Placeholder('detail_id'))        

        if 'detail_id' not in obj_dict:
            if 'queue_id' not in obj_dict or 'proxy_id' not in obj_dict:
                raise Exception("cannot update detail without a detail id, queue id, or proxy id")
            where_sql = sql.SQL("{0}={1} AND {2}={3}").format(sql.Identifier('queue_id'),sql.Placeholder('queue_id'),sql.Identifier('proxy_id'),sql.Placeholder('proxy_id'))        
            
            

        set_sql = sql.SQL(', ').join([sql.SQL("{0}={1}").format(sql.Identifier(k),sql.Placeholder(k)) for k in obj_dict.keys()])
        update = sql.SQL('UPDATE {0} SET {1} WHERE {2}').format(table_name,set_sql,where_sql)
        if cursor is not None:
            cursor.execute(update,obj.to_dict())
        else:
            self.do_query(update,obj.to_dict())

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
        self.insert_object(queue, 'queues','queue_id',cursor)
    
    def insert_proxy(self,proxy,cursor=None):
        self.insert_object(proxy,'proxies','proxy_id',cursor)

    def init_seed_details(self):
        seed_count = self.do_query("SELECT COUNT(*) as c FROM details WHERE queue_id=%(queue_id)s", {'queue_id':SEED_QUEUE_ID})[0]['c']

        cursor = self.cursor()
        if seed_count == 0:
            proxy_ids = [p['proxy_id'] for p in self.do_query("SELECT proxy_id FROM proxies")]
            for proxy_id in proxy_ids:
                insert_detail = "INSERT INTO details (proxy_id,queue_id) VALUES (%(proxy_id)s, %(queue_id)s);"
                params = {'proxy_id': proxy_id, 'queue_id': SEED_QUEUE_ID}
                cursor.execute(insert_detail,params)

        
        query = """
        BEGIN;
        LOCK TABLE details IN EXCLUSIVE MODE;
        SELECT setval('details_detail_id_seq', COALESCE((SELECT MAX(detail_id)+1 FROM details),1), false);
        COMMIT;
        """
        
        cursor.execute(query)
        cursor.close()

        
    def get_seed_details(self):
        self.init_seed_details()

        params = {'seed_queue_id': SEED_QUEUE_ID}
        query= """
            SELECT * FROM details 
            WHERE queue_id=%(queue_id)s
            AND active=%(active)s
            AND last_used < %(last_used_cutoff)s
            ORDER BY last_used ASC
            LIMIT %(limit)s;
            """
        a_params = {"queue_id":SEED_QUEUE_ID, "active":True,"limit": INITIAL_SEED_COUNT}
        ia_params = {"queue_id":SEED_QUEUE_ID, "active":False,"limit": INITIAL_SEED_COUNT}
        a_params['last_used_cutoff'] = LAST_USED_CUTOFF
        ia_params['last_used_cutoff'] = LAST_USED_CUTOFF
        active =  [Detail(**d) for d in self.do_query(query,a_params)]
        inactive = [Detail(**d) for d in self.do_query(query,ia_params)]
        
        return active + inactive

    def get_non_seed_details(self,queue_id):
        if queue_id is None:
            return []
        query= """
            SELECT * FROM details 
            WHERE queue_id = %(queue_id)s
            AND active=%(active)s
            AND last_used < %(last_used_cutoff)s
            ORDER BY last_used ASC
            LIMIT %(limit)s;
            """
        
        active_params = { 
            'queue_id': queue_id,
            'active': True,
            'last_used_cutoff': LAST_USED_CUTOFF,
            'limit': ACTIVE_LIMIT
        }

        inactive_params = {
            'queue_id': queue_id,
            'active': False,
            'last_used_cutoff': LAST_USED_CUTOFF,
            'limit': INACTIVE_LIMIT
        }

        active = [Detail(**d) for d in self.do_query(query, active_params)]
        
        inactive = [Detail(**d) for d in self.do_query(query, inactive_params)]


        return active + inactive

    def get_unused_proxy_ids(self,queue,count,excluded_pids):
        
        query = None
        excluded_pids.append(-1)
        excluded_pids.append(-2)

        params = {
            'seed_queue_id': SEED_QUEUE_ID,
            'limit': count,
            'active': True,
            'excluded_pids': tuple(excluded_pids)
        }
        
        if queue.id() is None:
            query = """
                SELECT proxy_id FROM details 
                WHERE queue_id = %(seed_queue_id)s
                AND active = %(active)s
                AND proxy_id NOT IN %(excluded_pids)s
                ORDER BY RANDOM()
                LIMIT %(limit)s
                """
            
        else:
            params['queue_id'] = queue.id()
            query = """
                SELECT proxy_id FROM details 
                WHERE queue_id = %(seed_queue_id)s 
                AND proxy_id NOT IN ( SELECT proxy_id FROM details WHERE queue_id = %(queue_id)s )
                AND proxy_id NOT IN %(excluded_pids)s
                AND active = %(active)s
                ORDER BY RANDOM()
                LIMIT %(limit)s
                """

        

        pids = [pid[0] for pid in self.do_query(query,params)]
        
        if len(pids) < count:
            params['count'] = count - len(pids)
            params['active'] = False
            result = self.do_query(query,params)
            for ipid in result:
                pids.append(ipid[0])

        return pids

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

        cursor = self.cursor()
        query = """
        BEGIN;
        LOCK TABLE queues IN EXCLUSIVE MODE;
        SELECT setval('queues_queue_id_seq', COALESCE((SELECT MAX(queue_id)+1 FROM queues),1), false);
        COMMIT;
        """
        cursor.execute(query)
        cursor.close()

        


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

    def get_proxy_by_address_and_port(self,address,port):
        query = "SELECT * FROM proxies where address=%(address)s AND port=%(port)s"
        params = {'address': address, 'port':port}
        cursor = self.cursor()
        cursor.execute(query,params)
        proxy_data = cursor.fetchone()
        if proxy_data is None:
            cursor.close()
            return None
        proxy = Proxy(**proxy_data)
        cursor.close()
        return proxy

    

        

class Redis(redis.Redis):
    def __init__(self,*args,**kwargs):
        pool = redis.BlockingConnectionPool(decode_responses=True, *args, **kwargs)
        super().__init__(connection_pool=pool)

class RedisDetailQueueEmpty(Exception):
    pass
class RedisDetailQueueInvalid(Exception):
    pass

class RedisDetailQueue(object):
    def __init__(self,queue,active=True):
        self.redis_mgr = RedisManager()

        self.redis = self.redis_mgr.redis
        self.queue = queue
        self.active = active
        active_clause = "active"
        if not active:
            active_clause = "inactive"
        self.redis_key = 'redis_%s_detail_queue_%s' % (active_clause, self.queue.queue_key)



    def reload(self):
        details = self.redis_mgr.get_all_queue_details(self.queue.queue_key)
        self.clear()
        for detail in details:
            if detail.active == self.active:
                self.enqueue(detail)


    def _update_blacklist_status(self,detail):
        if detail.blacklisted:
            last_used = detail.last_used
            now = datetime.utcnow()
            delta_t = now - last_used
            if delta_t.seconds > BLACKLIST_TIME and detail.blacklisted_count < MAX_BLACKLIST_COUNT:
                self.loger.info("unblacklisting detail")
                detail.blacklisted = False
                self.redis_mgr.update_detail(detail)
        
    
    def is_empty(self):
        if not self.redis.exists(self.redis_key):
            return True
        elif self.redis.llen(self.redis_key) == 0:
            return True
        else:
            return False

    def enqueue(self,detail):
        self._update_blacklist_status(detail)
        if detail.blacklisted:

            return

        proxy = self.redis_mgr.get_proxy(detail.proxy_key)
        if 'socks' in proxy.protocol:
    
            return
        
        detail_key = detail.detail_key
        detail_queue_key = self.redis.hget(detail_key,'queue_key')
        

        if detail_queue_key != self.queue.queue_key:
            raise RedisDetailQueueInvalid("No such queue key for detail")
        
        if detail.active != self.active:
            destination_queue = 'active'
            current_queue = "inactive"
            if self.active:
                destination_queue = 'inactive'
                current_queue = "active"

            correct_queue = RedisDetailQueue(self.queue, active=detail.active)
            return correct_queue.enqueue(detail)
            
        
        self.redis.rpush(self.redis_key,detail_key)



    def dequeue(self):
        if self.is_empty():
            raise RedisDetailQueueEmpty("No proxies available for queue key %s" % self.queue.queue_key)

        detail = Detail(**self.redis.hgetall(self.redis.lpop(self.redis_key)))
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

        self.redis.set("%s_%s" % (TEMP_ID_COUNTER, 'q'),0)
        self.redis.set("%s_%s" % (TEMP_ID_COUNTER, 'p'),0)
        self.redis.set("%s_%s" % (TEMP_ID_COUNTER, 'd'),0)

        queues = self.dbh.get_queues()




        for q in queues:
            self.register_queue(q)


        proxies = self.dbh.get_proxies()


        for p in proxies:
            self.register_proxy(p)

        

        seed_details = self.dbh.get_seed_details()




        seed_queue = self.get_queue_by_id(SEED_QUEUE_ID)
        seed_rdq = RedisDetailQueue(seed_queue)

        for seed_detail in seed_details:
            registered_detail = self.register_detail(seed_detail,bypass_db_check=True)




        #other_details = []
        """
        for q in queues:

            if q.queue_id != SEED_QUEUE_ID and q.queue_id != AGGREGATE_QUEUE_ID:
                details = self.dbh.get_non_seed_details(queue_id=q.queue_id)
                other_details.extend(details)
        
        


        for d in other_details:
            self.register_detail(d)

        """

    
    @block_if_syncing
    def register_object(self,key,obj):
        redis_key = key
        if obj.id() is None:
            temp_counter_key = "%s_%s" % (TEMP_ID_COUNTER, key)
            redis_key += 't_%s' % self.redis.incr(temp_counter_key)
        else:
            redis_key += '_%s' % obj.id()
        
        self.redis.hmset(redis_key,obj.to_dict(redis_format=True))
        return redis_key

    @block_if_syncing
    def register_queue(self,queue):
        queue_key = self.register_object('q',queue)
        self.redis.hmset(queue_key, {'queue_key': queue_key})

        return Queue(**self.redis.hgetall(queue_key))
    
    @queue_lock
    def initialize_queue(self,queue):

        if queue.id() is None:

            return
        
        existing_queue_details = self.dbh.get_non_seed_details(queue.queue_id)
        for existing_detail in existing_queue_details:
            detail = self.register_detail(existing_detail,bypass_db_check=True)


    @block_if_syncing
    def register_proxy(self,proxy):
        proxy_key = self.register_object('p',proxy)
        self.redis.hmset(proxy_key, {'proxy_key': proxy_key})
        return Proxy(**self.redis.hgetall(proxy_key))
    
    @block_if_syncing
    def register_detail(self,detail,bypass_db_check=False):
        if bypass_db_check and not self.is_syncing:
            logger.warn("attempting to bypass database check...")

        if detail.proxy_key is None or detail.queue_key is None:
            raise Exception('detail object must have a proxy and queue key')
        if not self.redis.exists(detail.proxy_key) or not self.redis.exists(detail.queue_key):
            raise Exception("Unable to locate queue or proxy for detail")

        detail_key = detail.detail_key

        if detail.queue_id is None or detail.proxy_id is None:
            # bypass db check as this must be a new detail (because queue and proxy are not in the database)
            bypass_db_check = True

        if not bypass_db_check:
            db_detail =  self.dbh.get_detail_by_queue_and_proxy(queue_id=detail.queue_id, proxy_id=detail.proxy_id)
            if db_detail is not None:
                raise DetailExistsException("Detail already exists in database.  Cannot register detail without deliberately bypassing database check")

        if self.redis.exists(detail.detail_key):
            raise DetailExistsException("Detail is already registered.")
            # return Detail(**self.redis.hgetall(detail_key))
        else:
            redis_data = detail.to_dict(redis_format=True)
            self.redis.hmset(detail_key,redis_data)
            if not bypass_db_check:
                self.redis.sadd(NEW_DETAILS_SET_KEY,detail_key)
        
        rdq = RedisDetailQueue(self.get_queue_by_key(detail.queue_key),active=detail.active)
        detail = self.get_detail(detail_key)
        rdq.enqueue(detail)
        return detail

    @block_if_syncing
    def get_detail(self,redis_detail_key):
        return Detail(**self.redis.hgetall(redis_detail_key))

    @block_if_syncing
    def get_all_queues(self):
        return [Queue(**self.redis.hgetall(q)) for q in self.redis.keys('q*')]

    def get_queue_by_domain(self,domain):
        queue_dict = {q.domain: q for q in self.get_all_queues()}
        if domain in queue_dict:
            return queue_dict[domain]
        
        return self.register_queue(Queue(domain=domain))

    @block_if_syncing
    def get_queue_by_id(self,qid):
        lookup_key = "%s_%s" % ('q',qid)
        if not self.redis.exists(lookup_key):
            raise Exception("No such queue with id %s" % qid)
        return Queue(**self.redis.hgetall(lookup_key))

    def get_queue_by_key(self,queue_key):
        return Queue(**self.redis.hgetall(queue_key))

    def get_proxy(self,proxy_key):
        return Proxy(**self.redis.hgetall(proxy_key))

    def update_detail(self,detail):
        self.redis.hmset(detail.detail_key,detail.to_dict(redis_format=True))
        self.redis.sadd(CHANGED_DETAILS_SET_KEY,detail.detail_key)

    def get_proxy_by_address_and_port(self,address,port):
        proxy_keys = self.redis.keys('p*')
        all_proxy_data = [self.redis.hgetall(pkey) for pkey in proxy_keys]
        for pd in all_proxy_data:
            if str(pd['address']) == str(address):
                if str(pd['port']) == str(port):
                    return Proxy(**pd)


        return None

    def get_all_queue_details(self, queue_key):
        key_match = 'd_%s*' % queue_key
        keys = self.redis.keys(key_match)
        details = [Detail(**self.redis.hgetall(key)) for key in keys]
        return details

    def get_queue_count(self,queue):
        key_match = 'd_%s*' % queue.queue_key
        return len(self.redis.keys(key_match))
        
            


class StorageManager(object):
    def __init__(self):
        self.redis_mgr = RedisManager()
        self.db_mgr = PostgresManager()

    def is_syncing(self):
        return self.redis_mgr.is_syncing()

    def new_proxy(self,address,port,protocol='http'):
        existing = self.redis_mgr.get_proxy_by_address_and_port(address,port)
        if existing is None:
            
            new_proxy = self.redis_mgr.register_proxy(Proxy(address,port,protocol))

            new_detail = Detail(proxy_key=new_proxy.proxy_key, queue_id=SEED_QUEUE_ID)
            try:
                self.redis_mgr.register_detail(new_detail)
                self.redis_mgr.redis.sadd(NEW_DETAILS_SET_KEY,new_detail.detail_key)
            except DetailExistsException:
                pass
            
        else:
            logger.warn("proxy already exists.")


    def get_seed_queue(self):
        return self.redis_mgr.get_queue_by_id(SEED_QUEUE_ID)
    
    @queue_lock
    def create_new_details(self,queue,count=ACTIVE_LIMIT+INACTIVE_LIMIT):

        fetched_pids_key = "%s%s" % (NEW_QUEUE_PROXY_IDS_PREFIX,queue.domain)
        fetched_pids = list(self.redis_mgr.redis.smembers(fetched_pids_key))
        proxy_ids = self.db_mgr.get_unused_proxy_ids(queue,count,fetched_pids)
        for proxy_id in proxy_ids:
            self.redis_mgr.redis.sadd(fetched_pids_key,proxy_id)
            proxy_key = 'p_%s' % proxy_id
            if not self.redis_mgr.redis.exists(proxy_key):
                raise Exception("Error while trying to create a new detail: proxy key does not exist in redis cache for proxy id %s" % proxy_id)
            
            if self.redis_mgr.redis.exists('d_%s_%s' % (queue.queue_key,proxy_key)):

                continue
            detail_kwargs = {'proxy_id': proxy_id, 'proxy_key': proxy_key, 'queue_id': queue.id(), 'queue_key': queue.queue_key}
            new_detail = Detail(**detail_kwargs)
            self.redis_mgr.register_detail(new_detail,bypass_db_check=True)

    
    def sync_to_db(self):
        logging.info("STARTING SYNC")
        new_queues = [Queue(**self.redis_mgr.redis.hgetall(q)) for q in self.redis_mgr.redis.keys("qt_*")]
        new_proxies = [Proxy(**self.redis_mgr.redis.hgetall(p)) for p in self.redis_mgr.redis.keys("pt_*")]
        new_detail_keys = set(self.redis_mgr.redis.keys('d_qt*') + self.redis_mgr.redis.keys('d_*pt*'))
        for ndk in new_detail_keys:
            self.redis_mgr.redis.sadd(NEW_DETAILS_SET_KEY, ndk)
        
        new_details = [Detail(**self.redis_mgr.redis.hgetall(d)) for d in list(new_detail_keys)]

        cursor = self.db_mgr.cursor()

        queue_keys_to_id = {}
        proxy_keys_to_id = {}
        for q in new_queues:
            self.db_mgr.insert_queue(q,cursor)
            queue_id = cursor.fetchone()[0]
            queue_keys_to_id[q.queue_key] = queue_id

        for p in new_proxies:
            try:
                self.db_mgr.insert_proxy(p,cursor)
                proxy_id = cursor.fetchone()[0]
                proxy_keys_to_id[p.proxy_key] = proxy_id
            except psycopg2.errors.UniqueViolation as e:

                # existing_proxy = self.db_mgr.get_proxy_by_address_and_port(p.address,p.port)
                proxy_keys_to_id[p.proxy_key] = None


        for d in new_details:
            if d.proxy_id is None:
                new_proxy_id = proxy_keys_to_id[d.proxy_key]
                if new_proxy_id is None:

                    continue
                else:
                    d.proxy_id = new_proxy_id
            if d.queue_id is None:
                d.queue_id = queue_keys_to_id[d.queue_key]
            self.db_mgr.insert_detail(d,cursor)
        

        changed_detail_keys = self.redis_mgr.redis.sdiff('changed_details','new_details')      
        changed_details = [Detail(**self.redis_mgr.redis.hgetall(d)) for d in self.redis_mgr.redis.sdiff('changed_details','new_details')]
        
        for changed in changed_details:
            if(changed.queue_id is None or changed.proxy_id is None):
                raise Exception("Unable to get a queue_id or proxy_id for an existing detail")
            
            self.db_mgr.update_detail(changed)
            


        cursor.close()
        self.redis_mgr.redis.flushall()
        logging.info("SYNC COMPLETE")
        return True

        


        
        
        


