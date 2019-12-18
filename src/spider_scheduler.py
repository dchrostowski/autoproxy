import requests
from IPython import embed
from autoproxy_config.config import configuration
import sys
import logging
import time
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


app_config = lambda config_val: configuration.app_config[config_val]['value']
SCRAPYD_API_URL = app_config('scrapyd_api_endpoint')

class ScrapydApi(object):

    @staticmethod
    def url(path):
        return "%s/%s" % (SCRAPYD_API_URL,path)

    @staticmethod
    def daemon_status():
        url = ScrapydApi.url('daemonstatus.json')
        resp = requests.get(url)
        return resp.json()

    @staticmethod
    def list_projects():
        url = ScrapydApi.url('listprojects.json')
        resp = requests.get(url)
        return resp.json()['projects']
    
    @staticmethod
    def list_spiders(project):
        url = ScrapydApi.url('listspiders.json')
        resp = requests.get(url, params={'project':project})
        return resp.json()['spiders']

    @staticmethod
    def schedule(project,spider):
        logging.info("TO DO")
        url = ScrapydApi.url('schedule.json')
        resp = requests.post(url,data={'project': project, 'spider':spider})
        return resp.json()



class SpiderScheduler(object):
    def __init__(self):
        daemon_status = None

        while daemon_status is None:
            try:
                daemon_status = ScrapydApi.daemon_status()
            except requests.exceptions.ConnectionError:
                logging.info("scrapyd server refused connection, will keep trying.")
                time.sleep(5)

        if daemon_status['status'] == 'ok':
            project_list = ScrapydApi.list_projects()
            self.project_spiders = {}
            
            for project in project_list:
                self.project_spiders[project] = ScrapydApi.list_spiders(project)


    def run_spiders(self):
        for project, spiders in self.project_spiders.items():
            # idk why there are 2 fake spiders but this is the easiest fix
            spiders = spiders[2:]
            for spider in spiders:
                logging.info("starting %s" % spider)
                resp = ScrapydApi.schedule(project,spider)
                logging.info(resp)


if __name__ == "__main__":
    scheduler = SpiderScheduler()
    scheduler.run_spiders()