import os
import json
import re
import logging

CONFIG_ENV = os.environ.get('AUTOPROXY_ENV','local')

CUR_DIR, _ = os.path.split(__file__)
CONFIG_DIR = os.path.join(CUR_DIR,'config')
#logging.basicConfig(filename='%s/log/api.log' % CWD, format='%(asctime)s - %(message)s', level=logging.DEBUG)

class ConfigReader(dict):
    def __init__(self):
        
        
        config_key_to_files = {
            'redis_config': "%s/redis_config.%s.json" % (CONFIG_DIR,CONFIG_ENV),
            'db_config': "%s/db_config.%s.json" % (CONFIG_DIR,CONFIG_ENV),
            'app_config': "%s/app_config.json" % CONFIG_DIR
        }
        config_keys = []

        for key,file in config_key_to_files.items():
            with open(file) as ifh:
                self.update({key:json.load(ifh)})
                config_keys.append(key)
            
        self.update({'configurations': config_keys})
        for k in self.keys():
            setattr(self,k,self[k])
        

configuration = ConfigReader()

