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

# Logging Configuration
BASE_LOG_PATH = os.environ.get("ECHALOASUERTE_LOGS_PATH", "/var/log/echaloasuerte/")
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s.%(msecs)03d] %(levelname)s %(name)s:%(module)s.%(funcName)s | %(message)s',
            'datefmt': '%Y%m%d %H:%M:%S',
        },
    },
    'handlers': {
        'log_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_LOG_PATH, 'echaloasuerte_log.txt'),
            'maxBytes': 1024 * 1024 * 30,  # 30 MB
            'backupCount': 5,
        },
        'error_log_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_LOG_PATH, 'echaloasuerte_err.txt'),
            'maxBytes': 1024 * 1024 * 30,  # 30 MB
            'backupCount': 5,
        },
        'debug_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': os.path.join(BASE_LOG_PATH, 'echaloasuerte_debug.txt'),
            'maxBytes': 1024 * 1024 * 30,  # 30 MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['debug_log_file'],
            'level': 'DEBUG',
        },
        'eas': {
            'handlers': ['debug_log_file'],
            'level': 'DEBUG',
        },
        '': {
            'handlers': ['log_file', 'error_log_file'],
            'level': 'DEBUG',
        },
    }
}
