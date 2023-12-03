"""Settings for deployment to the DEV/TEST server"""
from .prod import *

ADMIN_ENABLED = True

RAVEN_CONFIG["environment"] = "dev"

PAYPAL_MODE = "sandbox"
PAYPAL_ID = (
    "AUoNbxkShLicONf0kssMlkgUo91p2x-62izyrGc0YGpUDvrR2CtW0RjWAN0dX6qR2RTAkeWMIq2R0dYa"
)
SECRET_SANTA_QUEUE_URL = os.environ.get(
    "EAS_SQS_SS_QUEUE_URL",
    "https://sqs.us-east-2.amazonaws.com/059860094276/eas-backend-secret-santa-email-test",
)
