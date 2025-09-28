"""Settings for local development and tests"""
from .base import *

DEBUG = True
ADMIN_ENABLED = True

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

# Allow frontend origin(s) explicitly (not "*")
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

# Allow cookies (credentials)
CORS_ALLOW_CREDENTIALS = True


# Add browsable UI for DRF
DEFAULT_RENDERER_CLASSES.append("rest_framework.renderers.BrowsableAPIRenderer")

PAYPAL_MODE = "sandbox"
REVOLUT_MODE = "sandbox"
PAYPAL_ID = (
    "AUoNbxkShLicONf0kssMlkgUo91p2x-62izyrGc0YGpUDvrR2CtW0RjWAN0dX6qR2RTAkeWMIq2R0dYa"
)

SECRET_SANTA_QUEUE_URL = os.environ.get(
    "EAS_SQS_SS_QUEUE_URL",
    "https://sqs.us-east-2.amazonaws.com/059860094276/eas-backend-secret-santa-email-test",
)
