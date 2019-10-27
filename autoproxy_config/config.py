import os
import json
import re
from IPython import embed
import logging
CWD = os.path.dirname(os.path.realpath(__file__))
#logging.basicConfig(filename='%s/log/api.log' % CWD, format='%(asctime)s - %(message)s', level=logging.INFO)

class ConfigReader(dict):
    def __init__(self,config_dir=CWD, file_regex=r'([^\.]+)\.json'):
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
        

config_dict = ConfigReader()
