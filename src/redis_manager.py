

import redis

class RedisManager(object):
    def __init__(self):
        self.redis = redis.Redis(host='redis', port=6379)