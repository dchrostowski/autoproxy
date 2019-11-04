from urllib.parse import urlparse
import re
import random


def parse_domain(url):
    parsed = urlparse(url)
    domain = re.search(r'([^\.]+\.[^\.]+$)',parsed.netloc).group(1)
    return domain

def flip_coin(prob):
    mark = prob * 100
    print("mark is %s" % mark)
    result = random.random() * 100
    print("result is %s" %result)

    if result < mark:
        return True
    return False

    
