import configparser
import os
AUTOPROXY_ENV = os.environ.get('AUTOPROXY_ENV','local')
SCRAPYD_CFG_FILE = os.environ.get('SCRAPYD_CFG_FILE','scrapy.cfg')
print(SCRAPYD_CFG_FILE)
config = configparser.ConfigParser()
config.read(SCRAPYD_CFG_FILE)

deploy_section_env = "deploy:%s" % AUTOPROXY_ENV
SCRAPYD_USERNAME = config[deploy_section_env]['username']
SCRAPYD_PASSWORD = config[deploy_section_env]['password']

os.system("htpasswd -b -c /etc/nginx/htpasswd %s %s" % (SCRAPYD_USERNAME, SCRAPYD_PASSWORD))