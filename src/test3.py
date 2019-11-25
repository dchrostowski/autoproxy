from proxy_manager import ProxyManager
from storage_manager import StorageManager, RedisManager, RedisDetailQueue
from IPython import embed
rm = RedisManager()
rm.redis.flushall()
pm = ProxyManager()


for i in range(5):
    proxy = pm.get_proxy('https://proxydb.net')
    embed()