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
while not rdq.is_empty():
    detail = rdq.dequeue()
    print(detail.last_used)