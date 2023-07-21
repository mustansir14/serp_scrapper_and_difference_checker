# celery.py

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "serp_checker.settings")

app = Celery("serp_checker")


app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
