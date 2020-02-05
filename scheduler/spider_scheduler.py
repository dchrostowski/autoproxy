import requests
import sys
import os
import logging
from threading import Thread
import queue
import time
import datetime
import itertools
from scrapy_autoproxy.config import configuration
from scrapy_autoproxy.storage_manager import StorageManager

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
from requests.auth import HTTPBasicAuth


import configparser
import os

SCRAPYD_CFG_FILE = os.environ.get('SCRAPYD_CFG_FILE', 'scrapy.cfg')
config = configparser.ConfigParser()
config.read(SCRAPYD_CFG_FILE)

AUTOPROXY_ENV = os.environ.get('AUTOPROXY_ENV','local')



deploy_section_env = "deploy:%s" % AUTOPROXY_ENV
SCRAPYD_API_URL = config[deploy_section_env]['url']
SCRAPYD_USERNAME = config[deploy_section_env]['username']
SCRAPYD_PASSWORD = config[deploy_section_env]['password']
MAX_JOBS = int(config['autoproxy:scheduler']['max_jobs'])
SYNC_INTERVAL = int(config['autoproxy:scheduler']['sync_interval'])
SCRAPYD_JOB_TIMEOUT = int(config['autoproxy:scheduler']['job_timeout'])


class Task(object):
    def __init__(self,*args,**kwargs):
        self.fn = kwargs.pop('fn')
        self.requeue = kwargs.pop('requeue',False)
        self.args = args
        self.kwargs = kwargs

    def execute(self):
        self.fn(*self.args,**self.kwargs)

class TaskQueue(object):
    def __init__(self):
        self.queue = queue.Queue()
        self.thread = Thread(target=self.worker)
        self.thread.daemon = True
        self.thread.start()

    def enqueue(self,task):
        self.queue.put(task)

    @staticmethod
    def task_fn(*args,**kwargs):
        raise Exception("No task function defined!  Either override this method or pass a function to the TaskQueue.")

    def worker(self):
        while True:
            task = self.queue.get()
            if task is None:
                self.queue.task_done()
                break
            task.execute()
            self.queue.task_done()
            if task.requeue:
                self.enqueue(task)

    def finish(self):
        self.queue.put(None)
        self.queue.join()
        self.thread.join()

class ScrapydApi(object):

    @staticmethod
    def url(path):
        return "%s/%s" % (SCRAPYD_API_URL,path)

    @staticmethod
    def auth():
        return HTTPBasicAuth(SCRAPYD_USERNAME,SCRAPYD_PASSWORD)

    @staticmethod
    def daemon_status():
        url = ScrapydApi.url('daemonstatus.json')
        resp = requests.get(url, auth=ScrapydApi.auth())
        return resp.json()

    @staticmethod
    def list_projects():
        url = ScrapydApi.url('listprojects.json')
        resp = requests.get(url, auth=ScrapydApi.auth())
        return resp.json()['projects']
    
    @staticmethod
    def list_spiders(project):
        url = ScrapydApi.url('listspiders.json')
        resp = requests.get(url, params={'project':project}, auth=ScrapydApi.auth())
        
        return resp.json().get('spiders',[])

    @staticmethod
    def schedule(project,spider):
        url = ScrapydApi.url('schedule.json')
        resp = requests.post(url,data={'project': project, 'spider':spider}, auth=ScrapydApi.auth())
        if resp.json()['status'] == 'ok':
            logging.info("OK")
        else:
            logging.warning("Error while scheduling spider: %s" % resp.json()['message'] )
            return None

    @staticmethod
    def list_jobs(project):
        url = ScrapydApi.url('listjobs.json')
        resp = requests.get(url, params={'project':project}, auth=ScrapydApi.auth())
        return resp.json()

    @staticmethod
    def cancel_job(project,job_id):
        url = ScrapydApi.url('cancel.json')
        resp = requests.post(url, data={"project":project, "job":job_id}, auth=ScrapydApi.auth())
        logging.info(resp.json())
        return resp.json()




class SpiderScheduler(object):
    def __init__(self):
        daemon_status = None
        while daemon_status is None:
            try:
                daemon_status = ScrapydApi.daemon_status()
            except Exception as e:
                logging.error(e)
                logging.info("Problem connecting to scrapyd, retrying...")
                time.sleep(5)

        if daemon_status['status'] == 'ok':
            self.start_time = datetime.datetime.now()
            self.allow_new_jobs = True
            projects = []
            available_projects = ScrapydApi.list_projects()
            
            self.project_spiders = {}

            for project in available_projects:
                available_spiders = ScrapydApi.list_spiders(project)
                if len(available_spiders) > 0:
                    projects.append(project)
                    self.project_spiders[project] = available_spiders[2:]
            self.projects = projects

    def all_spiders(self):
        for project, spiders in self.project_spiders.items():
            for spider in spiders:
                yield {"project": project, "spider": spider}

    def get_timed_out_jobs(self,project=None):
        projects = self.projects
        if project is not None:
            projects = [project]
        timed_out = []

        for project in projects:
            active_jobs = self.active_jobs(project)
            for job in active_jobs:
                job_start_date = job.get('start_time',None)
                if job_start_date is not None:
                    job_start_date = datetime.datetime.fromisoformat(job_start_date)
                    now = datetime.datetime.utcnow()
                    elapsed = now - job_start_date
                    if elapsed.seconds > SCRAPYD_JOB_TIMEOUT:
                        job['project'] = project
                        job['elapsed_seconds'] = elapsed.seconds
                        timed_out.append(job)
        
        return timed_out



    def active_jobs(self, project=None, spider=None):
        num_active_jobs = 0
        if spider is not None and project is None:
            raise Exception("Must specifiy a project with spider")
        
        projects = self.projects
        
        if project is not None:
            projects = [self.projects]

        def filter_jobs(job):
            if spider is not None:
                if spider == job['spider']:
                    return True
                return False
            return True

        active_jobs = []
        for project in projects:
            jobs = ScrapydApi.list_jobs(project)
            pending_jobs = filter(filter_jobs,jobs['pending'])
            running_jobs = filter(filter_jobs,jobs['running'])
            
            active_jobs.extend(list(pending_jobs) + list(running_jobs))

        return active_jobs


    def spider_generator(self,project):
        for spider in self.project_spiders[project]:
            yield {'project':project,'spider':spider}

    def run_spiders(self):
        for project, spiders in self.project_spiders.items():
            # idk why there are 2 fake spiders but this is the easiest fix
            spiders = spiders[2:]
            for spider in spiders:
                logging.info("starting %s" % spider)
                resp = ScrapydApi.schedule(project,spider)
                logging.info(resp)

            

tq = TaskQueue()

if __name__ == "__main__":
    scheduler = SpiderScheduler()
    all_active_jobs = scheduler.active_jobs()
    streetscrape_active_jobs = scheduler.active_jobs('autoproxy','streetscrape')
    proxydb_active_jobs = scheduler.active_jobs('autoproxy','proxydb')

    def schedule_spider(project,spider):
        ScrapydApi.schedule(project,spider)

    def do_sync():
        while len(scheduler.active_jobs()) > 0:
            logging.info('waiting for the jobs to stop')
            logging.info("there are %s active jobs" % len(scheduler.active_jobs()))
            timed_out_jobs = scheduler.get_timed_out_jobs()
            if len(timed_out_jobs) > 0:
                logging.warning("There are %s timed out jobs" % len(timed_out_jobs))
                for toj in timed_out_jobs:
                    to_project = toj['project']
                    to_jid = toj['id']
                    to_spider = toj['spider']
                    logging.info("Terminating %s job with id %s " % (to_spider,to_jid))
                    ScrapydApi.cancel_job(to_project,to_jid)



            time.sleep(5)
        logging.info("STARTING SYNC...")
        storage_mgr = StorageManager()
        storage_mgr.sync_to_db()
        logging.info("SYNC COMPLETE")
        now = datetime.datetime.now()
        scheduler.start_time = now
        scheduler.allow_new_jobs = True
        


    spider_gen = scheduler.spider_generator('autoproxy')
    for spider in itertools.cycle(spider_gen):
        if len(scheduler.active_jobs(**spider)) < MAX_JOBS:
            if scheduler.allow_new_jobs:
                logging.info("enqueueing task to schedule %s" % spider)
                tq.enqueue(Task(**spider,fn=schedule_spider))
        
        now = datetime.datetime.now()
        start = scheduler.start_time
        elapsed = now - start
        logging.info("elapsed time since last sync: %s" % elapsed.seconds)
        if elapsed.seconds > SYNC_INTERVAL and scheduler.allow_new_jobs:
            logging.info("enqueuing sync task")
            scheduler.allow_new_jobs = False
            tq.enqueue(Task(fn=do_sync))
        
        time.sleep(5)
