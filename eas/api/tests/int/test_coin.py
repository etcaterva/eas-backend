from rest_framework.test import APILiveServerTestCase

from eas.api.models import Coin

from ..factories import CoinFactory
from .common import DrawAPITestMixin


class TestSpinner(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = "coin"
    Model = Coin
    Factory = CoinFactory
