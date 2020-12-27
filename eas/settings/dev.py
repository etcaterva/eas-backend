"""Settings for deployment to the DEV/TEST server"""
from .prod import *

ADMIN_ENABLED = True

RAVEN_CONFIG["environment"] = "dev"
