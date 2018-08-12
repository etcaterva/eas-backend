"""Production deployment settings"""
import os

import raven

from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'HOST': 'db',
        'PORT': 5432,
    }
}


# Sentry config
INSTALLED_APPS = [
    *INSTALLED_APPS,
    'raven.contrib.django.raven_compat',
]

RAVEN_CONFIG = {
    'dsn': os.environ.get('SENTRY_DSN'),
    'release': raven.fetch_git_sha(ROOT_DIR),
    'environment': 'prod',
}
