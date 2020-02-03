# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

from setuptools import setup

setup(
    name='scrapy_autoproxy',
    version='0.3.0',
    description='Machine learning proxy picker',
    long_description=open('README.rst').read(),
    keywords='scrapy proxy web-scraping',
    license='MIT License',
    author="Dan Chrostowski",
    author_email='dan@streetscrape.com',
    url='https://streetscrape.com',
    packages=[
        'scrapy_autoproxy',
    ],
    package_dir={'scrapy_autoproxy': 'scrapy_autoproxy'},
    package_data={'scrapy_autoproxy': ['config/app_config.json','config/db_config.docker.json','config/redis_config.docker.json','config/redis_config.local.json','config/db_config.local.json']},
    install_requires=[
        'redis',
        'psycopg2-binary'
    ],
)
