import unittest
from src.proxy_objects import Queue, Proxy, Detail

class TestStringMethods(unittest.TestCase):

    def test_object_ids(self):
        proxy = Proxy(address="foobar", port=80, proxy_id=4)
        queue = Queue(domain='google.com', queue_id=3)
        detail = Detail(proxy_id=proxy,queue_id=queue)
        self.assertEqual(detail.proxy_id, proxy.id())
        self.assertEqual(detail.queue_id, queue.id())

if __name__ == '__main__':
    unittest.main()