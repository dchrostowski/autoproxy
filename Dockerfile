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

RUN python3 -m pip install --upgrade \
		setuptools \
		wheel && \
	python3 -m pip install --upgrade scrapy
WORKDIR /code
ENV FLASK_APP src/app.py
ENV FLASK_RUN_HOST 0.0.0.0
ENV PYTHONPATH=$PYTHONPATH:/code
#RUN apt-get install gcc musl-dev linux-headers postgresql-dev gcc python3-dev musl-dev
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
#RUN pip3 install -r requirements.txt
COPY . .
CMD ["python3", "src/app.py"]
CMD ["flask", "run"]