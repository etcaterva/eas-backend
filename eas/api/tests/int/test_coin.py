from rest_framework.test import APILiveServerTestCase

from eas.api.models import Coin
from .common import DrawAPITestMixin
from ..factories import CoinFactory


class TestSpinner(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = 'coin'
    Model = Coin
    Factory = CoinFactory
