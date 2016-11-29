FROM python:3.5
MAINTAINER Ville Koivunen <ville.koivunen@hel.fi>
RUN mkdir /code
RUN apt-get update && apt-get install -y libgdal1h postgresql-client-9.4
ADD . /code/
ADD Docker/apiserver/docker-entrypoint.sh /code/docker-entrypoint.sh
RUN chmod +x /code/docker-entrypoint.sh
WORKDIR /code
RUN mv Docker/apiserver/docker-django-settings.py local_settings.py
RUN pip install -r requirements.txt && pip install uwsgi
