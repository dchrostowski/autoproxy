from proxy_manager import ProxyManager
from autoproxy_config.config import configuration
DESIGNATED_ENDPOINT = configuration.app_config['designated_endpoint']['value']
from IPython import embed
import time


pm = ProxyManager()
pm.storage_mgr.redis_mgr.redis.flushall()
pm = ProxyManager()
for i in range(500):
    proxy = pm.get_proxy(DESIGNATED_ENDPOINT)
    proxy.callback(success=False)


pm.storage_mgr.sync_to_db()
