#!/bin/bash

# Parameters
UWSGI_PROCESSES=4
UWSGI_THREADS=1

# Collect static files
echo "Collect static files"
python manage.py collectstatic --noinput

# From https://github.com/City-of-Helsinki/infopankki-api/blob/master/compose/django/entrypoint.sh
# (Naturally it would be better to have Django handle database disturbances by itself)
function postgres_ready(){
python << END
import sys
import psycopg2
try:
    conn = psycopg2.connect(dbname="postgres", user="postgres", password="postgres", host="db")
except psycopg2.OperationalError:
    sys.exit(-1)
sys.exit(0)
END
}

until postgres_ready; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

# Put hstore extension in place
echo CREATE EXTENSION IF NOT EXISTS hstore | python manage.py dbshell

# Apply database migrations
echo "Apply database migrations"
python manage.py migrate

# Start server
echo "Starting server"
uwsgi --http 0.0.0.0:8000 --wsgi-file respa/wsgi.py --callable application \
      --processes $UWSGI_PROCESSES --threads $UWSGI_THREADS --master \
      --reload-on-rss 300 --chunked-input-limit 10485760
