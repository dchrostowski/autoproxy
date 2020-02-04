FROM python:3.7
RUN mkdir /scheduler
RUN mkdir /code
COPY ./autoproxy /code/autoproxy
COPY ./autoproxy_package /code/autoproxy_package
COPY ./scheduler /scheduler
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r /scheduler/requirements.txt
RUN python3 -m pip install scrapyd-client
#RUN pip install git+https://github.com/scrapy/scrapyd-client
RUN cd /code/autoproxy_package && python3 setup.py build && python3 setup.py install
WORKDIR /code/autoproxy
ENV AUTOPROXY_ENV=docker
ENV SCRAPYD_CFG_FILE=/code/autoproxy/scrapy.cfg
ENTRYPOINT scrapyd-deploy docker && python3 /scheduler/spider_scheduler.py
