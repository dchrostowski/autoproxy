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
		zlib1g-dev \
		nginx \
		apache2-utils && \
	apt-get clean && \
	rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/* /tmp/* /var/tmp/*
RUN pip3  install  --upgrade pip

COPY requirements.txt requirements.txt

RUN pip3 install  --upgrade \
		setuptools \
		wheel && \
		pip3  install -r requirements.txt && \
		pip3 install  --upgrade scrapy && \
		pip3 install --upgrade scrapyd

RUN mkdir /start
ADD ./scrapyd/scrapyd.conf /etc/scrapyd/scrapyd.conf
ADD ./scrapyd/nginx.conf /etc/nginx/sites-enabled/default
ADD ./scrapyd/start_scrapyd.sh /start/start_scrapyd.sh
ADD ./scrapyd/scrapyd.env /start/scrapyd.env
RUN chmod +x /start/start_scrapyd.sh

RUN mkdir /code
COPY ./middleware /code/middleware/
COPY ./autoproxy_config /code/autorpoxy_config/
ENV PYTHONPATH=/code/middleware:/code:/usr/local/lib/python3.7/dist-packages/scrapyd/scripts:$PYTHONPATH
RUN ls /code
RUN ls /code/middleware
RUN echo $PYTHONPATH
EXPOSE 6800
WORKDIR /start
ENTRYPOINT sh /start/start_scrapyd.sh

