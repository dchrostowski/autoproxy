from IPython import embed
import time
from storage_manager import StorageManager, RedisManager, RedisDetailQueue

sm = StorageManager()
new_proxy = sm.create_proxy('1.1.1.3',8080,'http')
rdq1 = RedisDetailQueue(queue_key='q_1')
tq1 = sm.create_queue('https://www.google.com')

rdq2 = RedisDetailQueue(queue_key=tq1.queue_key)


for i in range(5000):
    detail_to_clone = rdq1.dequeue()
    clone = sm.clone_detail(detail_to_clone,tq1)

for i in range(rdq2.length()):
    detail = rdq2.dequeue()
    #print("-----------------------")
    #print(detail.to_dict())
    #print("-----------------------")
    




