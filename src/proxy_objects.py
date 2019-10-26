from IPython import embed
from datetime import datetime
import time


class Proxy(object):
    AVAILABLE_PROTOCOLS = ('http', 'https', 'socks5', 'socks4')

    def __init__(self, address, port, protocol='http', proxy_id=None):
        self.address = address
        self.port = port

        if protocol not in self.__class__.AVAILABLE_PROTOCOLS:
            raise Exception("Invalid protocol %s" % protocol)
        self.protocol = protocol
        self._proxy_id = proxy_id
        self.id = self.proxy_id

    def urlify(self):
        return "%s://%s:%s" % (self.protocol, self.address, self.port)

    @property
    def proxy_id(self):
        if(self._proxy_id) is None:
            print("todo handle proxy id")
            return None
        return self._proxy_id



class Detail(object):

    def reconcile_ids(self,id_object):
        if isinstance(id_object,int):
            return id_object
        if id_object is None:
            return None
        return id_object.id

    def __init__(self, active=False, load_time=None, last_updated=None, last_active=None, last_used=None, bad_count=9, blacklisted=False, blacklisted_count=0, lifetime_good=0, lifetime_bad=0,proxy=None,queue=None,detail_id=None):
        self.active = active
        self._load_time = load_time
        self.last_active = last_active,
        self.last_used = last_used
        self.bad_count = bad_count
        self.blacklisted = blacklisted
        self.blacklisted_count = blacklisted_count
        self.lifetime_good = lifetime_good
        self.lifetime_bad = lifetime_bad
        self._detail_id = detail_id
        self.id = detail_id
        self.proxy_id = self.reconcile_ids(proxy)
        self.queue_id = self.reconcile_ids(queue)

    @property
    def load_time(self):
        return self._load_time

    @load_time.setter
    def load_time(self,delta_t):
        print("load time setter")
        self._load_time = delta_t.microseconds * 0.001
    

    @property
    def detail_id(self):
        if(self._detail_id is None):
            print("todo handle detail id")
            return None
        return self._detail_id

class Queue(object):
    def __init__(self,domain,queue_id=None):
        self.domain = domain
        self._queue_id = queue_id
    
    @property
    def queue_id(self):
        if(self._queue_id) is None:
            print("todo handle detail id")
            return None
        return self._queue_id

class ProxyObject(Proxy):
    def __init__(self,proxy,queue,detail):
        if detail.proxy_id != proxy.proxy_id:
            raise Exception("Detail/Proxy mismatch on proxy id")
        if detail.queue_id != queue.queue_id:
            raise Exception("Detail/Queue mismatch on queue id")

        self._proxy = proxy
        self._queue = queue
        self._detail = detail

        self.dispatch_time = None
        self.load_time = self._detail._load_time

        super().__init__(self._proxy.address, self._proxy.port, self._proxy.protocol, self._proxy.id)

  
    def dispatch(self):
        self.dispatch_time = datetime.now()

    def callback(self,success):
        print("dispatched at %s" % self.dispatch_time)
        print("it is now %s" % datetime.now())
        self._detail.load_time = datetime.now() - self.dispatch_time
        if(success):
            print("success")
        else:
            print("failure")
        


    


p = Proxy('a', 32)
d = Detail()
q = Queue('streetscrape.com')
proxy = ProxyObject(p,q,d)
proxy.dispatch()
time.sleep(2)
proxy.callback(True)

embed()
