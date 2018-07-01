from django.test import TestCase
from ws.models import *
from .factories import RandomNumberFactory


class TestModels(TestCase):

    def setUp(self):
        self.rn = RandomNumberFactory()

    @staticmethod
    def get_random_number(id_):
        return RandomNumber.objects.get(id=id_)

    def test_creation_success(self):
        rn = RandomNumberFactory(
            range_min=1,
            range_max=1,
        )
        rn.save()
        rn.toss()

        self.assertEqual(
            1,
            self.get_random_number(rn.id).results.first().value
        )

    def test_limit_of_results(self):
        res1 = self.rn.toss()
        for i in range(RandomNumber._RESULT_LIMIT - 1):
            self.rn.toss()

        self.assertIn(res1, self.rn.results.all())

        self.assertEqual(self.rn.results.count(), 50)
        self.rn.toss()
        self.assertEqual(self.rn.results.count(), 50)
        self.assertNotIn(res1, self.rn.results.all())
