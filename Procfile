release: python manage.py migrate
web: gunicorn gestion_creditos.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --log-file -
