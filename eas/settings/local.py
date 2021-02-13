"""Settings for local development and tests"""
from .base import *

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(ROOT_DIR / "db.sqlite3"),
    }
}

# Enable Cross-Origin Resource Sharing for local development
INSTALLED_APPS = [
    *INSTALLED_APPS,
    "corsheaders",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    *MIDDLEWARE,
]
CORS_ORIGIN_ALLOW_ALL = True
ALLOWED_HOSTS = ["*"]


# Add browsable UI for DRF
DEFAULT_RENDERER_CLASSES.append("rest_framework.renderers.BrowsableAPIRenderer")

PAYPAL_MODE = "sandbox"
PAYPAL_ID = (
    "AUoNbxkShLicONf0kssMlkgUo91p2x-62izyrGc0YGpUDvrR2CtW0RjWAN0dX6qR2RTAkeWMIq2R0dYa"
)
