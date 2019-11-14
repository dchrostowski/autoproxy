from urllib.parse import urlparse
import re
import random
import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def parse_domain(url):
    parsed = urlparse(url)
    domain = re.search(r'([^\.]+\.[^\.]+$)',parsed.netloc).group(1)
    return domain

def flip_coin(prob):
    mark = prob * 100
    result = random.random() * 100
    if result < mark:
        return True
    return False

    
