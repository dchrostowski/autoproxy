from IPython import embed
import time
from storage_manager import StorageManager, RedisManager, RedisDetailQueue

sm = StorageManager()
tq1 = sm.create_queue('https://www.google.com')
tq2 = sm.create_queue('https://streetscrape.com')
rdq1 = RedisDetailQueue(queue_key='q_1')
rdq2 = RedisDetailQueue(queue_key=tq1.queue_key)
cloned = []
for i in range(rdq1.length()):
    detail_to_clone = rdq1.dequeue()
    clone = sm.clone_detail(detail_to_clone,tq1)
    cloned.append(detail_to_clone)

for c in cloned:
    rdq1.enqueue(c)

dup_clone = sm.clone_detail(cloned[0],tq1)
embed()


