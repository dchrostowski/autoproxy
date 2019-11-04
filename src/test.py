from IPython import embed
import time
from storage_manager import StorageManager, RedisManager, RedisDetailQueue

sm = StorageManager()

new_proxy = sm.create_proxy('1.1.1.3',8080,'http')
new_proxy = sm.create_proxy('1.1.1.4',8080,'http')
new_proxy = sm.create_proxy('1.1.1.5',8080,'http')
rdq1 = RedisDetailQueue(queue_key='q_1', active=False)
tq1 = sm.create_queue('https://www.google.com')
tq2 = sm.create_queue('https://www.bing.com')

rdq2 = RedisDetailQueue(queue_key=tq1.queue_key)


for i in range(rdq1.length()):
    detail_to_clone = rdq1.dequeue()
    clone = sm.clone_detail(detail_to_clone,tq1)
    clone = sm.clone_detail(detail_to_clone,tq2)


sm.sync_to_db()

embed()