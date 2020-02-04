from urllib.parse import urlparse
import re
import random
import sys


from datetime import datetime


def parse_domain(url):
    parsed = urlparse(url)
    domain = re.search(r'([^\.]+\.[^\.]+$)',parsed.netloc).group(1)
    return domain

def flip_coin(prob):
    prob = prob * 100
    result = random.randint(0,100)
    if result < prob:
        return True
    
    return False

def format_redis_boolean(bool_val):
    if bool_val == True:
        return '1'
    elif bool_val == False:
        return '0'

    else:
        raise Exception("invalid boolean")

def format_redis_timestamp(datetime_object):
    if type(datetime_object) != datetime:
        raise Exception("invalid type while formatting datetime to str")
    return datetime_object.isoformat()

def parse_boolean(val):
    if(val == '1' or val == 1 or val == True):
        return True
    elif(val == '0' or val == 0 or val == False):
        return False
    else:
        raise Exception("Invalid value for proxy object boolean")

def parse_timestamp(timestamp_val):
    if type(timestamp_val) == datetime:
        return timestamp_val

    if type(timestamp_val) == str:
        try:
            return datetime.strptime(timestamp_val, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
           return  datetime.strptime(timestamp_val, "%Y-%m-%dT%H:%M:%S")

    else:
        raise Exception("Invalid type for proxy object timestamp")
