from rest_framework.test import APILiveServerTestCase

from eas.api.models import Spinner

from ..factories import SpinnerFactory
from .common import DrawAPITestMixin


class TestSpinner(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = "spinner"
    Model = Spinner
    Factory = SpinnerFactory
