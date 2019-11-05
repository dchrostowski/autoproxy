from storage_manager import Redis
from proxy_manager import ProxyManager
from autoproxy_config.config import configuration
DESIGNATED_ENDPOINT = configuration.app_config['designated_endpoint']['value']
from IPython import embed
import time

redis = Redis(**configuration.redis_config)
pm = ProxyManager()

embed()

pm = ProxyManager()
for i in range(500):
    proxy = pm.get_proxy(DESIGNATED_ENDPOINT)
    proxy.callback(success=False)
    proxy = pm.get_proxy('https://google.com')
    proxy.callback(success=True)



pm.storage_mgr.sync_to_db()
