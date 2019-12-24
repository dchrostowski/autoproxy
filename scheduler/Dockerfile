FROM python:3
RUN mkdir /scheduler
RUN mkdir /code
COPY ./autoproxy /code/autoproxy
RUN ls /code/autoproxy
COPY ./scheduler /scheduler
#RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r /scheduler/requirements.txt
RUN python3 -m pip install -r /code/autoproxy/requirements.txt
RUN pip install git+https://github.com/scrapy/scrapyd-client
ENV AUTOPROXY_ENV='docker'
ENV PYTHONPATH="${PYTHONPATH}:/code/autoproxy/autoproxy_middleware"

ENTRYPOINT ["python3", "/scheduler/foo.py"]
