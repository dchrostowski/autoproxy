import redis
import sys
import os

CWD = os.path.dirname(os.path.realpath(__file__))




class RedisManager(object):
    CWD = os.path.dirname(os.path.realpath(__file__))

    def __init__(self):
        self.redis = redis.Redis(host='redis', port=6379)

redis_manager = RedisManager()
cache = redis_manager.redis
