from IPython import embed
import time
from storage_manager import StorageManager, RedisManager, RedisDetailQueue

sm = StorageManager()
q = sm.create_queue('https://www.google.com')
q = sm.create_queue('https://streetscrape.com')
print(q)
temp_queues = sm.redis_mgr.get_all_temp_id_queues()
print(temp_queues)


rdq = RedisDetailQueue(queue_key="q_1")
embed()

for i in range(6):
    detail = rdq.dequeue()
    print("---------------------------")
    print("detail key: %s" % detail.detail_key)
    print("detail id: %s" % detail.detail_id)
    print("detail last used: %s" % detail.last_used)
    print("-----------------------------")
    rdq.enqueue(detail)
    embed()