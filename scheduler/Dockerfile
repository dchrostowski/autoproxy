FROM python:3
RUN mkdir /scheduler
RUN mkdir /code
COPY ./autoproxy /code/autoproxy/
COPY ./middleware /code/autoproxy/
COPY ./autoproxy_config /code/autoproxy/autoproxy_config

COPY ./scheduler /scheduler
#RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r /scheduler/requirements.txt
RUN pip install git+https://github.com/scrapy/scrapyd-client
ENV PYTHONPATH="${PYTHONPATH}:/code"
ENV PYTHONPATH="${PYTHONPATH}:/code/autoproxy"
WORKDIR /code/autoproxy
ENTRYPOINT ["python3", "/scheduler/foo.py"]
