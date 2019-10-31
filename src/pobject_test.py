from proxy_objects import Detail

class Foo(object):
    def __init__(self):
        pass

    def get_detail(self):
        return Detail()
    
    def get_detail_dict(self):
        return self.get_detail().to_dict()

class Bar(object):
    def __init__(self):
        pass
    
    def get_detail(self):
        return Detail()

    def get_detail_dict(self):
        return self.get_detail().to_dict()

foo = Foo()
bar = Bar()

foo.get_detail_dict()
bar.get_detail_dict()