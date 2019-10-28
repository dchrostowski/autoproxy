import redis
import psycopg2
import sys
import os
import logging

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


class RedisManager(object):
    def __init__(self):
        logging.info("redis manager init")
        self.redis = redis.Redis(**configuration.redis_config)
        self.postgres_manager = PostgresManager()


        init = self.redis.get('init')
        logging.info("value of init is: %s" % init)

        if init is None:
            self.sync_from_db()

    def sync_from_db(self):
        with self.redis.pipeline() as pipe:
            pipe.watch('next_proxy_id','next_queue_id','next_detail_id')
            try:
                queries = {
                    'proxies': 'SELECT * FROM proxies;', 
                    'details': 'SELECT * FROM details;',
                    'queues':  'SELECT * FROM queues;'
                }
                data = {}
                cursor = self.postgres_manager.cursor()
                for table,query in queries.items():
                    print("executing %s" % query)
                    cursor.execute(query)
                    data[table] = cursor.fetchall()

                proxy_object_instances = {
                        'proxies': [Proxy(**p) for p in data['proxies']],
                        'queues': [Queue(**q) for q in data['queues']],
                        'details': [Detail(**d) for d in data['details']]
                }

                get_ids_query = """
                SELECT
                nextval(pg_get_serial_sequence('proxies','proxy_id')) as proxies,
                nextval(pg_get_serial_sequence('queues','queue_id')) as queues,
                nextval(pg_get_serial_sequence('details','detail_id')) as details;
                """
                cursor = self.postgres_manager.cursor()
                cursor.execute(get_ids_query)
                next_ids = cursor.fetchone()
                logging.info(next_ids)
                pipe.multi()
                pipe.set('next_proxy_id',next_ids['proxies'])
                pipe.set('next_queue_id',next_ids['queues'])
                pipe.set('next_detail_id',next_ids['details'])
                pipe.set('init',1)
                pipe.execute()
            except redis.WatchError:
                logging.warning("WatchError while trying to reset proxy object ids")

                return self.sync_from_db()



        #self.save_to_cache(proxy_object_instances, next_ids)

    def save_to_cache(self,pqd_objects, next_ids):
        
            


        


        
        

        embed()





        

            




redis_manager = RedisManager()
cache = redis_manager.redis
