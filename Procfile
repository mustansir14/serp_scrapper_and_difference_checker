web: gunicorn serp_checker.wsgi
worker: celery -A serp_checker worker --loglevel=info
beat: celery -A serp_checker beat --loglevel=info