import time
import os
import sys
import redis
#from storage_manager import cache
import flask
import subprocess
from flask import request
from IPython import embed
from storage_manager import StorageManager


print("here")

app = flask.Flask(__name__)

def get_hit_count():
    retries = 5
    while True:
        try:
            return cache.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)


@app.route('/')
def hello():
    
    #count = get_hit_count()
    return 'hello world'
    #return 'Hello World! I have been seen {} times.\n'.format(count)

@app.route('/runspider')
def runspider():
    request_args = request.args
    count = int(request_args.get('count',1))
    spider = request_args.get('spider','streetscrape')

    cmd = 'cd /code/autoproxy/autoproxy/spiders && scrapy runspider %s.py -a count=%s' % (spider, count)
    def inner():
        proc = subprocess.Popen(cmd,shell=True,stderr=subprocess.PIPE)
        for line in iter(proc.stderr.readline, ''):
            time.sleep(0.1)
            yield str(line.decode('utf-8').rstrip()) + '<br/>\n'

    return flask.Response(inner(),mimetype='text/html')
    
    #call =  subprocess.call('cd /code/autoproxy/autoproxy/spiders && scrapy runspider streetscrape.py', shell=True)

@app.route('/sync_to_db')
def sync_to_db():
    storage_mgr = StorageManager()
    sync_success = storage_mgr.sync_to_db()
    return {'sync success': sync_success}

@app.route('/sync_from_db')
def sync_from_db():
    storage_mgr = StorageManager()
    storage_mgr.redis_mgr.redis.flushall()
    storage_mgr = StorageManager()
    sync_success = not storage_mgr.redis_mgr.redis.exists('syncing')
    return {'sync success': sync_success}
