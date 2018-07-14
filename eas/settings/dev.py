"""Settings for deployment to the DEV/TEST server"""
from .base import *

ALLOWED_HOSTS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(ROOT_DIR / 'db.sqlite3'),
    }
}
