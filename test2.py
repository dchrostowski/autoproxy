from scrapy_autoproxy.config import configuration
from scrapy_autoproxy.storage_manager import StorageManager, Redis
from scrapy_autoproxy.proxy_manager import ProxyManager
from IPython import embed
import random
import time

redis = Redis(**configuration.redis_config)

sm = StorageManager()
pm = ProxyManager()

details = sm.redis_mgr.get_all_queue_details('qt_1')

active_details = []
inactive_details = []
for detail in details:
    if detail.active:
        active_details.append(detail)
    else:
        inactive_details.append(detail)

print("active details: %s" % len(active_details))
print("inactive details: %s" % len(inactive_details))


embed()