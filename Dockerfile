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
RUN pip3 install --upgrade pip
RUN python3 -m pip install --upgrade \
		setuptools \
		wheel && \
	python3 -m pip install --upgrade scrapy

#RUN apt-get install gcc musl-dev linux-headers postgresql-dev gcc python3-dev musl-dev
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
#RUN pip3 install -r requirements.txt
COPY . .
ENV PYTHONPATH=/code/src:/code:$PYTHONPATH

WORKDIR /code/autoproxy/autoproxy/spiders
CMD ["scrapy", "runspider", "streetscrape.py"]
#CMD ["scrapy", "runspider", "autoproxy/autoproxy/spiders/streetscrape.py"]
WORKDIR /code
ENV FLASK_APP src/app.py
ENV FLASK_RUN_HOST 0.0.0.0
CMD ["python3", "src/app.py"]
CMD ["flask", "run"]