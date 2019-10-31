from IPython import embed
from datetime import datetime
import time
from random import randint

class Proxy(object):
    AVAILABLE_PROTOCOLS = ('http', 'https', 'socks5', 'socks4')

    def __init__(self, address, port, protocol='http', proxy_id=None):
        self.address = address
        self.port = port
        if protocol not in self.__class__.AVAILABLE_PROTOCOLS:
            raise Exception("Invalid protocol %s" % protocol)
        self.protocol = protocol
        self.proxy_id = proxy_id
        

    def urlify(self):
        return "%s://%s:%s" % (self.protocol, self.address, self.port)

    def id(self):
        return self.proxy_id

    def to_dict(self):
        obj_dict = {
            "address": self.address,
            "port":  self.port,
            "protocol": self.protocol,
        }

        if self.proxy_id is not None:
            obj_dict.update({'proxy_id', self.proxy_id})


class Detail(object):
    def proxy_object_id(self,object_or_id):
        if isinstance(object_or_id,int) or object_or_id is None:
            return object_or_id
        return object_or_id.id()

    def __init__(self, active=False, load_time=None, last_updated=None, last_active=None, last_used=None, bad_count=9, blacklisted=False, blacklisted_count=0, lifetime_good=0, lifetime_bad=0, proxy=None, queue=None, detail_id=None):
        self.active = active
        self.load_time = load_time
        self.last_active = last_active,
        self.last_used = last_used
        self.bad_count = bad_count
        self.blacklisted = blacklisted
        self.blacklisted_count = blacklisted_count
        self.lifetime_good = lifetime_good
        self.lifetime_bad = lifetime_bad
        
        self.proxy_id = self.proxy_object_id(proxy)
        self.queue_id = self.proxy_object_id(queue)
        self.detail_id = detail_id
    
    def id(self):
        return self.detail_id
    

    def to_dict(self):
        obj_dict =  {
            "active": self.active,
            "load_time": self.load_time,
            "last_used": self.last_used,
            "bad_count": self.bad_count,
            "blacklisted": self.blacklisted,
            "blacklisted_count": self.blacklisted_count,
            "lifetime_good": self.lifetime_good,
            "lifetime_bad": self.lifetime_bad,
            "proxy_id": self.proxy_id,
            "queue_id": self.queue_id,
        }
        
        if self.detail_id is not None:
            obj_dict.update({'detail_id': self.detail_id})
        return obj_dict


class Queue(object):
    def __init__(self, domain, queue_id=None):
        self.domain = domain
        self.queue_id = queue_id

    def id(self):
        return self.queue_id
    
    def to_dict(self):
        obj_dict = {
            "domain": self.domain,
        }

        if(self.queue_id is not None):
            obj_dict.update({"queue_id": self.queue_id})
        
        return obj_dict



class ProxyObject(Proxy):
    def __init__(self, proxy, queue, detail):
        if detail.proxy_id != proxy.proxy_id:
            raise Exception("Detail/Proxy mismatch on proxy id")
        if detail.queue_id != queue.queue_id:
            raise Exception("Detail/Queue mismatch on queue id")

        self.proxy = proxy
        self.queue = queue
        self.detail = detail

        self.dispatch_time = None

        super().__init__(self.proxy.address, self.proxy.port,
                         self.proxy.protocol, self.proxy.id)

    def dispatch(self):
        self.dispatch_time = datetime.now()

    def callback(self, success):
        print("dispatched at %s" % self.dispatch_time)
        print("it is now %s" % datetime.now())
        self.detail.load_time = datetime.now() - self.dispatch_time
        self.dispatch_time = None
        if(success):
            print("success")
        else:
            print("failure")
