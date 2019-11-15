FROM debian:buster
RUN apt-get update && \
	apt-get install --assume-yes --no-install-recommends \
		gcc \
		libffi-dev \
		libssl-dev \
		libxml2-dev \
		libxslt1-dev \
		python3-pip \
		python3-dev \
		zlib1g-dev && \
	apt-get clean && \
	rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/* /tmp/* /var/tmp/*
RUN pip3 install  --upgrade pip

COPY requirements.txt requirements.txt

RUN python3 -m pip install  --upgrade \
		setuptools \
		wheel && \
		python3 -m pip install -r requirements.txt && \
		python3 -m pip install  --upgrade scrapy


#RUN pip3 --proxy=proxy-fg1.bcbsmn.com:9119 --trusted-host pypi.python.org --trusted-host pypi.org --trusted-host files.pythonhosted.org install -r requirements.txt
RUN mkdir /code
WORKDIR /code
COPY . .
ENV PYTHONPATH=/code/src:/code:$PYTHONPATH

ENV FLASK_APP /code/src/app.py
ENV FLASK_RUN_HOST 0.0.0.0
CMD ["python3", "/code/src/app.py"]
CMD ["flask", "run"]
#WORKDIR /code/autoproxy/autoproxy/spiders
#CMD ["scrapy", "runspider", "streetscrape.py"]
#CMD ['python3']