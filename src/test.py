from IPython import embed
import time
from storage_manager import RedisManager
from proxy_objects import Detail
rm = RedisManager()
dkeys = rm.redis.keys('d*')
redis_detail = rm.redis.hgetall(dkeys[0])
detail = Detail(**redis_detail)
embed()