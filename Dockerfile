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
RUN pip3  install  --upgrade pip

COPY requirements.txt requirements.txt

RUN python3 -m pip  install  --upgrade \
		setuptools \
		wheel && \
		python3 -m pip  install -r requirements.txt && \
		python3 -m pip  install  --upgrade scrapy && \
		python3 -m pip  install --upgrade scrapyd && \
        python3 -m pip  install --upgrade scrapyd-client


RUN mkdir /code
COPY . /code
ENV PYTHONPATH=/code/src:/code:/usr/local/lib/python3.7/dist-packages/scrapyd/scripts:$PYTHONPATH
EXPOSE 6800
WORKDIR /code/autoproxy
CMD ["scrapyd"]

