import os

from celery import Celery
from django.conf import settings

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    raise RuntimeError("Set 'DJANGO_SETTINGS_MODULE' env variable")


app = Celery(broker=settings.CELERY_BROKER_URL)
app.config_from_object("django.conf:settings")
app.autodiscover_tasks(settings.INSTALLED_APPS)
