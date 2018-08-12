"""Settings for deployment to the DEV/TEST server"""
from .prod import *

RAVEN_CONFIG['environment'] = 'dev'
