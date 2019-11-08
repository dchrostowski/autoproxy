import time
import os
import sys
import redis
#from storage_manager import cache
import flask
import subprocess

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
    cmd = 'cd /code/autoproxy/autoproxy/spiders && scrapy runspider streetscrape.py'
    def inner():
        proc = subprocess.Popen(cmd,shell=True,stderr=subprocess.PIPE)
        for line in iter(proc.stderr.readline, ''):
            time.sleep(1)
            yield str(line.decode('utf-8').rstrip()) + '<br/>\n'

    return flask.Response(inner(),mimetype='text/html')
    
    #call =  subprocess.call('cd /code/autoproxy/autoproxy/spiders && scrapy runspider streetscrape.py', shell=True)
    return 'hi'

