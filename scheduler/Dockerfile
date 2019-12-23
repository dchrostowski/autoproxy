FROM python:3
RUN mkdir /scheduler
RUN mkdir /code
COPY ./middleware /code/middleware/
COPY ./autoproxy_config /code/autoproxy_config/
COPY ./autoproxy /code/autoproxy/
COPY ./scheduler /scheduler
#RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r /scheduler/requirements.txt
RUN pip install git+https://github.com/scrapy/scrapyd-client
ENV PYTHONPATH="${PYTHONPATH}:/code"
ENV PYTHONPATH="${PYTHONPATH}:/code/middleware"
WORKDIR /code/autoproxy
ENTRYPOINT ["python3", "/scheduler/foo.py"]
