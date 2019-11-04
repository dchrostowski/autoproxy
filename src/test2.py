from proxy_manager import ProxyManager
from autoproxy_config.config import configuration
DESIGNATED_ENDPOINT = configuration.app_config['designated_endpoint']['value']
from IPython import embed
import time


pm = ProxyManager()
proxy = pm.get_proxy(DESIGNATED_ENDPOINT)
print(proxy.to_dict())
time.sleep(2)
proxy.callback(success=True)
print(proxy.to_dict())

pm.storage_mgr.sync_to_db()