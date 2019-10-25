class Proxy(object):
    AVAILABLE_PROTOCOLS = ('http','https','socks5','socks4')
    def __init__(self, address, port, protocol, proxy_id=None):
        self.address = address
        self.port = port

        if protocol not in AVAILABLE_PROTOCOLS:
            raise Exception("Invalid protocol %s" % protocol)
        self.protocol = protocol

    def urlify(self):
        return "%s://%s:%s" % (self.protocol, self.address, self.port)

    