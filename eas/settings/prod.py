"""Production deployment settings"""
import os

import raven

from .base import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres",
        "HOST": "db",
        "PORT": 5432,
    }
}


# Sentry config
INSTALLED_APPS = [
    *INSTALLED_APPS,
    "raven.contrib.django.raven_compat",
]

RAVEN_CONFIG = {
    "dsn": os.environ.get("SENTRY_DSN"),
    "release": raven.fetch_git_sha(ROOT_DIR),
    "environment": "prod",
}

# Logging Configuration
BASE_LOG_PATH = os.environ.get("ECHALOASUERTE_LOGS_PATH", "/var/log/echaloasuerte/")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s.%(msecs)03d] %(levelname)s %(name)s:%(module)s.%(funcName)s | %(message)s",
            "datefmt": "%Y%m%d %H:%M:%S",
        },
    },
    "handlers": {
        "log_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": os.path.join(BASE_LOG_PATH, "echaloasuerte_log.txt"),
            "maxBytes": 1024 * 1024 * 100,  # 100 MB
            "backupCount": 5,
        },
        "error_log_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": os.path.join(BASE_LOG_PATH, "echaloasuerte_err.txt"),
            "maxBytes": 1024 * 1024 * 30,  # 50 MB
            "backupCount": 2,
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["log_file"],
            "level": "INFO",
        },
        "eas": {
            "handlers": ["log_file"],
            "level": "INFO",
        },
        "": {
            "handlers": ["log_file", "error_log_file"],
            "level": "DEBUG",
        },
    },
}

PAYPAL_MODE = "live"
REVOLUT_MODE = "live"
PAYPAL_ID = (
    "AfcsuQa3-9RejIysZLXVsQewL6uMirZjPWORj5fYvV3OrQmEiTECsp0Ol4-R3D2YgU7EPIgEaaGKTC5H"
)
SECRET_SANTA_QUEUE_URL = (
    "https://sqs.us-east-2.amazonaws.com/059860094276/eas-backend-secret-santa-email"
)
