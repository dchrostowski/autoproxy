FROM python:3.7-alpine
WORKDIR /code
ENV FLASK_APP src/app.py
ENV FLASK_RUN_HOST 0.0.0.0
ENV PYTHONPATH=$PYTHONPATH:/code
RUN apk add --no-cache gcc musl-dev linux-headers postgresql-dev gcc python3-dev musl-dev
COPY requirements.txt requirements.txt
#RUN pip3 install --proxy proxy-fg1.bcbsmn.com:9119 --trusted-host=pypi.org --trusted-host=files.pythonhosted.org -r requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD ["python3", "src/app.py"]
CMD ["flask", "run"]