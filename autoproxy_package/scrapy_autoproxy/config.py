import os
import json
import re
from IPython import embed
import logging

CONFIG_ENV = os.environ.get('AUTOPROXY_ENV','local')

CUR_DIR, _ = os.path.split(__file__)
CONFIG_DIR = os.path.join(CUR_DIR,'config')
#logging.basicConfig(filename='%s/log/api.log' % CWD, format='%(asctime)s - %(message)s', level=logging.INFO)

class ConfigReader(dict):
    def __init__(self,config_dir=CONFIG_DIR, file_regex=r'([^\.]+)\.json'):
        #files = [f for f in os.listdir(config_dir) if re.match(file_regex, f)]
        #config_keys = [re.search(file_regex,f).group(1) for f in files]

        config_keys = []
        self.update({'files': [f for f in os.listdir(config_dir) if re.match(file_regex, f)]})
        
        for f in self['files']:
            
            with open("%s/%s" % (config_dir,f)) as ifh:

                config_data = json.load(ifh)
                config_key = re.search(file_regex,f).group(1) 
                self.update({config_key: config_data})
                config_keys.append(config_key)
            
        #self.update({'files':files})            
        self.update({'configurations': config_keys})
        for k in self.keys():
            setattr(self,k,self[k])
        

configuration = ConfigReader()

