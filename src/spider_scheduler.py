import requests
from IPython import embed
from autoproxy_config.config import configuration
import sys
import logging
from threading import Thread
import queue
import time
import datetime
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


app_config = lambda config_val: configuration.app_config[config_val]['value']
SCRAPYD_API_URL = app_config('scrapyd_api_endpoint')
MAX_JOBS = app_config('scrapyd_max_jobs_per_spider')


class Task(object):
    def __init__(self,*args,**kwargs):
        self.fn = kwargs.pop('fn')
        self.requeue = kwargs.pop('requeue',True)
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
            self.have_synced = False
            project_list = ScrapydApi.list_projects()
            self.project_spiders = {}
            
            for project in project_list:
                self.project_spiders[project] = ScrapydApi.list_spiders(project)[2:]

    def all_spiders(self):
        for project, spiders in self.project_spiders.items():
            for spider in spiders:
                yield {"project": project, "spider": spider}


    def run_spiders(self):
        for project, spiders in self.project_spiders.items():
            # idk why there are 2 fake spiders but this is the easiest fix
            spiders = spiders[2:]
            for spider in spiders:
                logging.info("starting %s" % spider)
                resp = ScrapydApi.schedule(project,spider)
                logging.info(resp)


def check_kwargs(**kwargs):
    print("check kwargs: project: %s spider: %s" % (kwargs.get('project',None), kwargs.get('spider',None)))

tq = TaskQueue()
def main():
    scheduler = SpiderScheduler()
    projects = scheduler.project_spiders.keys()


    def number_of_jobs_left():
        num_jobs_left = 0
        for project in projects:
            jobs_info = ScrapydApi.list_jobs(project)
            pending_and_running = len(jobs_info['pending']) + len(jobs_info['running'])
            num_jobs_left += pending_and_running
        
        return num_jobs_left

    def sync_when_there_are_no_jobs():
        job_count = number_of_jobs_left()
        while job_count > 0:
            time.sleep(5)
            job_count = number_of_jobs_left()
            print("there are %s jobs left." % job_count)

        print("all the jobs are done")
        print("no morestart the sync now")
        print("syncing...")
        time.sleep(5)
        print("done syncing")
        scheduler.have_synced = True
    
    def schedule_spider(*args,**kwargs):
        some_delta = datetime.datetime.now() - scheduler.start_time
        if some_delta.seconds % 3 == 0:
            ScrapydApi.schedule(kwargs['project'],kwargs['spider'])
        time.sleep(4)
        print("there are %s jobs scheduled" % number_of_jobs_left())


    for i in range(MAX_JOBS):
        for kwargs in scheduler.all_spiders():
            tq.enqueue(Task(**kwargs, fn=schedule_spider))
            
    elapsed_time = datetime.datetime.now() - scheduler.start_time

    while elapsed_time.seconds < 5000:
        print("not time to sync yet")
        time.sleep(3)
        current_time = datetime.datetime.now()
        print("current itme is %s" % current_time)
        print("scheduler start time was %s" % scheduler.start_time)
        elapsed_time = current_time - scheduler.start_time
        print("elapsed seconds: %s" % elapsed_time.seconds)
    
    print("sync task has been enqueued")
    tq.enqueue(Task(fn=sync_when_there_are_no_jobs,requeue=False))
    

    while not scheduler.have_synced:
        time.sleep(5)
        print("awaiting sync...")
    
    return main()
            

    

        
        



    #tq = TaskQueue(default_task_fn=)

if __name__ == "__main__":
    main()