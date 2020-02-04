import sys

from scrapy.core.downloader.handlers.http11 import TunnelError
from twisted.internet.error import TimeoutError, ConnectError, ConnectionRefusedError, NoRouteError
from twisted.web._newclient import ResponseNeverReceived
from scrapy.exceptions import IgnoreRequest

EXCEPTIONS_COLLECTION_1 = [TimeoutError, ConnectError, ResponseNeverReceived, ConnectionRefusedError, NoRouteError, TunnelError, IgnoreRequest]

class ExceptionManager(object):
    def __init__(self):
        pass

    def is_defective_proxy(self,exception):
        
        if type(exception) in EXCEPTIONS_COLLECTION_1:
            return True

        return False

