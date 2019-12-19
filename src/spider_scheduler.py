import requests
from IPython import embed
from autoproxy_config.config import configuration
import sys
import logging
from threading import Thread
import queue
import time
import datetime
import itertools
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


app_config = lambda config_val: configuration.app_config[config_val]['value']
SCRAPYD_API_URL = app_config('scrapyd_api_endpoint')
MAX_JOBS = app_config('scrapyd_max_jobs_per_spider')


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
        url = ScrapydApi.url('schedule.json')
        resp = requests.post(url,data={'project': project, 'spider':spider})
        if resp.json()['status'] == 'ok':
            print("OK")
        else:
            logging.warn("Error while scheduling spider: %s" % resp.json()['message'] )
            return None

    @staticmethod
    def list_jobs(project):
        url = ScrapydApi.url('listjobs.json')
        resp = requests.get(url, params={'project':project})
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
            self.start_time = datetime.datetime.now()
            self.allow_new_jobs = True
            project_list = ScrapydApi.list_projects()
            self.project_spiders = {}
            
            for project in project_list:
                self.project_spiders[project] = ScrapydApi.list_spiders(project)[2:]

            self.projects = project_list

    def all_spiders(self):
        for project, spiders in self.project_spiders.items():
            for spider in spiders:
                yield {"project": project, "spider": spider}

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
            print('waiting for the jobs to stop')
            print("there are %s active jobs" % len(scheduler.active_jobs()))
            time.sleep(5)
        print("STARTING SYNC...")
        time.sleep(5)
        print("SYNC COMPLETE")
        now = datetime.datetime.now()
        scheduler.start_time = now
        scheduler.allow_new_jobs = True
        


    spider_gen = scheduler.spider_generator('autoproxy')
    for spider in itertools.cycle(spider_gen):
        if len(scheduler.active_jobs(**spider)) < 4:
            if scheduler.allow_new_jobs:
                print("enqueueing task to schedule %s" % spider)
                if spider['spider'] == 'streetscrape':
                    tq.enqueue(Task(**spider,fn=schedule_spider))
        
        now = datetime.datetime.now()
        start = scheduler.start_time
        elapsed = now - start
        print("elapsed time since last sync: %s" % elapsed.seconds)
        if elapsed.seconds > 60 and scheduler.allow_new_jobs:
            print("enqueuing sync task")
            scheduler.allow_new_jobs = False
            tq.enqueue(Task(fn=do_sync))
        
        time.sleep(2)