"""Settings for deployment to the DEV/TEST server"""
from .prod import *

ADMIN_ENABLED = True

RAVEN_CONFIG["environment"] = "dev"

PAYPAL_MODE = "sandbox"
PAYPAL_ID = (
    "AUoNbxkShLicONf0kssMlkgUo91p2x-62izyrGc0YGpUDvrR2CtW0RjWAN0dX6qR2RTAkeWMIq2R0dYa"
)
