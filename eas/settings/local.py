"""Settings for local development and tests"""
from .base import *

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(ROOT_DIR / 'db.sqlite3'),
    }
}

# Enable Cross-Origin Resource Sharing for local development
INSTALLED_APPS = [
    *INSTALLED_APPS,
    'corsheaders',
]
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    *MIDDLEWARE,
]
CORS_ORIGIN_ALLOW_ALL = True


# Add browsable UI for DRF
DEFAULT_RENDERER_CLASSES.append(
    'rest_framework.renderers.BrowsableAPIRenderer'
)
