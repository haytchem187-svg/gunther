release: python manage.py makemigrations && python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn gestion_creditos.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --log-file -
