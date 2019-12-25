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

COPY ./autoproxy/requirements.txt requirements.txt

RUN pip3 install  --upgrade \
		setuptools \
		wheel && \
		pip3  install -r requirements.txt && \
		pip3 install --upgrade scrapyd

RUN mkdir /code
COPY ./autoproxy_package /code/autoproxy_package
RUN cd /code/autoproxy_package && python3 setup.py build && python3 setup.py install
RUN mkdir /start
ADD ./scrapyd/scrapyd.conf /etc/scrapyd/scrapyd.conf
ADD ./scrapyd/nginx.conf /etc/nginx/sites-enabled/default
ADD ./scrapyd/start_scrapyd.sh /start/start_scrapyd.sh
ADD ./scrapyd.env /start/scrapyd.env
RUN chmod +x /start/start_scrapyd.sh

ENV AUTOPROXY_ENV=docker
EXPOSE 6800
WORKDIR /start
ENTRYPOINT sh /start/start_scrapyd.sh

