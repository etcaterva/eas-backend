from rest_framework.test import APILiveServerTestCase

from eas.api.models import Spinner
from .common import DrawAPITestMixin
from ..factories import SpinnerFactory


class TestSpinner(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = 'spinner'
    Model = Spinner
    Factory = SpinnerFactory

